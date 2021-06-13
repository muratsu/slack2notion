import json
import os

from flask import Flask, request, make_response, redirect
from notion.client import NotionClient
from firebase_admin import credentials, firestore, initialize_app
from threading import Thread
from sentry_sdk import capture_exception

# Initialize Sentry
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
sentry_sdk.init(
    "https://452ebcba94fc42e296d596d82e262cbf@o480008.ingest.sentry.io/5526008",
    integrations=[FlaskIntegration()],
    traces_sample_rate=1,
    release="slack2notion-1.0.1"
)

import constants
from helper import helpStatement, commandLogic, followup, postRequest, clientSetup, errorMessageResp

# Initialize Flask app
app = Flask(__name__, template_folder='')

# Initialize Firestore DB
cred = credentials.Certificate('key.json')
if os.environ.get('RUNNING_ENV') == "production":
    cred = credentials.Certificate('prodKey.json')

default_app = initialize_app(cred)
db = firestore.client()
dbRef = db.collection('slack2notion')


@app.route('/', methods=['GET'])
def main():
    return "Hey there, it seems like you shouldnt be here", 200


@app.route('/redirect', methods=['GET'])
def exchangeToken():
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    returnURLBase = "http://localhost:3000"
    if state == "prod":
        returnURLBase = os.environ.get('PROD_URL')

    if error:
        return redirect(f'{returnURLBase}?error={error}')

    headers = {"Content-type": "application/x-www-form-urlencoded"}
    body = {
        "code": code,
        "client_id": os.environ.get('CLIENT_ID'),
        "client_secret": os.environ.get('CLIENT_SECRET'),
        "redirect_uri": 'https://slack2notion.glitch.me/redirect'
    }
    r = postRequest('https://slack.com/api/oauth.v2.access', body, headers)
    resp = r.json()
    
    sentry_sdk.set_context("/redirect", {
        "code": code
    })
    if state == "prod" and not resp["ok"]:
        capture_exception(resp)

    returnUrl = ""
    if resp["ok"]:
        dbUpdate = {}
        dbUpdate[resp["team"]["id"]] = resp["access_token"]
        dbRef.document("access-token").set(dbUpdate, merge=True)
        returnUrl = f'{returnURLBase}/redirect?app={os.environ.get("APP_ID")}&team={resp["team"]["id"]}'
    else:
        returnUrl = f'{returnURLBase}?error={resp["error"]}'

    return redirect(returnUrl)


@app.route('/events', methods=['POST'])
def events():
    data = request.json
    
    sentry_sdk.set_context("/events", data)

    if data["type"] == "url_verification":
        return data["challenge"], 200

    client = clientSetup(dbRef, data["team_id"])

    userId = data["event"]["user"]
    teamId = data["team_id"]
    slackUid = f'{teamId}-{userId}'

    updateHome(teamId, userId)

    slackUserRef = dbRef.document(slackUid).get()

    if not slackUserRef.exists or "hasOnboarded" not in slackUserRef.to_dict():
        print("first time", userId)

        try:
            response = client.chat_postMessage(
                channel=data["event"]["channel"],
                text=helpStatement(userId)
            )
            dbRef.document(slackUid).set({"hasOnboarded": True}, merge=True)
        except SlackApiError as e:
            return f"Error: {e}", 502

    return "", 200


@app.route('/interactive', methods=['POST'])
def interactive():
    payload = json.loads(request.form["payload"])
    
    sentry_sdk.set_context("/interactive", payload)

    client = clientSetup(dbRef, payload["user"]["team_id"])

    actoinType = payload["type"]
    userId = payload["user"]["id"]
    teamId = payload["user"]["team_id"]
    slackUid = f'{teamId}-{userId}'

    if actoinType == "block_actions":
        action = payload["actions"][0]["action_id"]
        value = payload["actions"][0]["value"]

        if action == "home_task":
            try:
                collectionName = executeCommand(
                    constants.TASK, slackUid, value)

                with open("confirmCreate.txt") as modalfile:
                    modalJson = json.load(modalfile)
                    modalJson["blocks"][0]["text"][
                        "text"] = f"✅ Successfully created a new task \"*{value}*\" to *{collectionName}*"

                    updateHome(teamId, userId)
                    client.views_open(
                        trigger_id=payload["trigger_id"], view=modalJson)
                    return "", 200

            except Exception as e:
                capture_exception(e)
                return f"Error: {e}", 502

        with open("modal.txt") as modalfile:
            modalJson = json.load(modalfile)

            if action == "home_token_v2":
                modalJson["blocks"].pop()
            elif action == "home_database":
                modalJson["blocks"] = modalJson["blocks"][1:]

            client.views_open(trigger_id=payload["trigger_id"], view=modalJson)

            return "", 200

    elif actoinType == "view_submission":
        if "token_v2" in payload["view"]["state"]["values"]:
            value = payload["view"]["state"]["values"]["token_v2"]["my_action"]["value"]

            try:
                executeCommand(constants.TOKEN, slackUid, value)
                updateHome(teamId, userId)
                return "", 200
            except Exception as e:
                capture_exception(e)
                return make_response(errorMessageResp(str(e), "token_v2"))

        elif "database_link" in payload["view"]["state"]["values"]:
            value = payload["view"]["state"]["values"]["database_link"]["my_action"]["value"]

            try:
                executeCommand(constants.DATABASE, slackUid, value)
                updateHome(teamId, userId)
                return "", 200
            except Exception as e:
                capture_exception(e)
                return make_response(errorMessageResp(str(e), "database_link"))

    return "", 200


@app.route('/slashcommand', methods=['GET', 'POST'])
def slashcommand():
    data = request.form.to_dict()
    print('/slashcommand', data)

    thr = Thread(target=slashBackgroundworker, args=[data])
    thr.start()

    return "", 200


def slashBackgroundworker(data):
    sentry_sdk.set_context("/slashcommand", data)
    
    textArgs = data["text"].split()

    responseUrl = data["response_url"]
    userId = data["user_id"]
    teamId = data["team_id"]

    command, commandValue = commandLogic(textArgs)
    print(command, commandValue)

    slackUid = f'{teamId}-{userId}'

    if command == constants.TOKEN:
        try:
            executeCommand(constants.TOKEN, slackUid, commandValue)
            return followup(responseUrl, "✅ Successfully set up token_v2", False)
        except Exception as e:
            capture_exception(e)
            return followup(responseUrl, f"Error: {e}", False)

    elif command == constants.DATABASE:
        try:
            colletionName = executeCommand(
                constants.DATABASE, slackUid, commandValue)
            return followup(responseUrl, f"✅ Successfully set up database *{colletionName}*", False)
        except Exception as e:
            capture_exception(e)
            return followup(responseUrl, f"Error: {e}", False)

    elif command == constants.TASK:
        try:
            collectionName = executeCommand(
                constants.TASK, slackUid, commandValue)

            return followup(responseUrl, f"✅ Successfully created a new task \"*{commandValue}*\" to *{collectionName}*", False)
        except Exception as e:
            capture_exception(e)
            return followup(responseUrl, f"Error: {e}", False)

    elif command == constants.STATUS:
        try:
            slackUserRef = dbRef.document(slackUid).get()

            if not slackUserRef.exists:
                return "No record is found 🙁", 200

            slackUser = slackUserRef.to_dict()

            result = ""

            if u'token_v2' in slackUser:
                result += "✅ token_v2 found\n"
            else:
                result += "No token_v2 found ❌ \n"

            if u'database' in slackUser:
                result += f"✅ database found {slackUser[u'database']['db_name']}\n"
            else:
                result += "No database found ❌ \n"

            return followup(responseUrl, result, True)
        except Exception as e:
            capture_exception(e)
            return followup(responseUrl, f"Error: {e}", False)

    elif command == constants.HELP:
        return followup(responseUrl, helpStatement(userId), True)
    else:
        return followup(responseUrl, f"Error: invalid request", False)

    return "", 200


def executeCommand(command, slackUid, value):
    print("executeCommand", command, slackUid, value)
    if command == constants.TOKEN:
        try:
            nClient = NotionClient(token_v2=value)
        except Exception:
            raise Exception("Invalid token_v2")

        dbRef.document(slackUid).set(
            {u'token_v2': value}, merge=True)
        return None

    elif command == constants.DATABASE:
        slackUserRef = dbRef.document(slackUid).get()

        if not slackUserRef.exists:
            raise Exception("Please set up token_v2 first")

        slackUser = slackUserRef.to_dict()

        if u'token_v2' not in slackUser:
            raise Exception("Please set up token_v2 first")

        try:
            nClient = NotionClient(token_v2=slackUser[u'token_v2'])
        except Exception:
            raise Exception("Unauthorized token_v2 was found")

        # Replace this URL with the URL of the page you want to edit
        cv = nClient.get_collection_view(value)

        colletionName = cv.collection.name
        if colletionName == "":
            colletionName = "Untitled"

        dbUpdate = {
            u'database': {
                u'db_link': value,
                u'db_name': colletionName,
                # TODO:
                # u'properties': []
            }
        }

        dbRef.document(slackUid).set(dbUpdate, merge=True)
        return colletionName

    elif command == constants.TASK:
        slackUserRef = dbRef.document(slackUid).get()

        if not slackUserRef.exists:
            raise Exception("Please set up token_v2 first")

        slackUser = slackUserRef.to_dict()

        if u'token_v2' not in slackUser:
            raise Exception("Please set up token_v2 first")
        if u'database' not in slackUser:
            raise Exception("Please set up database first")

        nClient = NotionClient(token_v2=slackUser[u'token_v2'])

        # Replace this URL with the URL of the page you want to edit
        cv = nClient.get_collection_view(slackUser[u'database']['db_link'])

        collectionName = slackUser[u'database']['db_name']
        row = cv.collection.add_row()
        row.name = value
        return collectionName


def updateHome(teamId, userId):
    tokenRef = dbRef.document("access-token").get()
    tokens = tokenRef.to_dict()
    token = tokens[teamId]

    slackUid = f'{teamId}-{userId}'
    print("updating...", userId, slackUid)
    slackUserRef = dbRef.document(slackUid).get()
    slackUser = slackUserRef.to_dict()

    with open("homeBlocks.txt") as homefile:
        homeJson = json.load(homefile)

        # add user name
        homeJson["blocks"][0]["text"]["text"] = homeJson["blocks"][0]["text"]["text"].format(
            user=userId)

        # update the token and database blocks
        if slackUser and u'token_v2' in slackUser:
            homeJson["blocks"][4]["text"]["text"] = "✅ Token_v2 is set"
            homeJson["blocks"][4]["accessory"]["style"] = "primary"
            homeJson["blocks"][4]["accessory"]["text"]["text"] = "Re-set"

        if slackUser and u'database' in slackUser:
            homeJson["blocks"][6]["text"]["text"] = f'✅ Database *{slackUser["database"]["db_name"]}* is set'
            homeJson["blocks"][6]["accessory"]["style"] = "primary"
            homeJson["blocks"][6]["accessory"]["text"]["text"] = "Re-set"

        body = {"user_id": userId, "view": homeJson}
        headers = {'Authorization': f"Bearer {token}",
                   "Content-type": "application/json"}

        resp = postRequest(
            "https://slack.com/api/views.publish", json.dumps(body), headers)


port = int(os.environ.get('PORT', 8080))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port)
