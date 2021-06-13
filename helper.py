import requests
import json
from slack import WebClient


def helpStatement(userId):
    result = f':wave: Hi <@{userId}>, here are some quick tips to get you started! \n\n'

    result += "*Setup your Notion account*\n"

    result += "You only need to do this once. Here is a tutorial on <https://www.notion.so/Find-Your-Notion-Token-e6a6451402d24515a86f640c87ca7d15 |finding Notion token>.\n"

    result += "`/slack2notion token [token_v2]` to link your Notion account. \n\n"

    result += "*Select default database*\n"
    result += "`/slack2notion database [database url]` to set a database where you want the task to be created at. \n\n"

    result += "*Add task*\n"
    result += "`/slack2notion task [task name]` to creat a new task.\n\n"

    result += "*Check settings*\n"
    result += "`/slack2notion status` to show the current token and database setting."

    return result


def commandLogic(textArgs):
    command, commandValue = "", ""

    if len(textArgs) == 2:
        command, commandValue = textArgs
    elif len(textArgs) == 1:
        command = textArgs[0]
    elif len(textArgs) == 0:
        command = "help"
    else:
        command = textArgs[0]
        commandValue = " ".join(textArgs[1:])

    return command, commandValue


def followup(responseUrl, text, isEphemeral):
    body = {"text": text}
    if isEphemeral:
        body["response_type"] = "ephemeral"

    postRequest(responseUrl, json.dumps(body))


def postRequest(url, body, headers=None):
    if headers:
        return requests.post(url, data=body, headers=headers)
    return requests.post(url, data=body)


def clientSetup(dbRef, teamId):
    tokenRef = dbRef.document("access-token").get()
    tokens = tokenRef.to_dict()

    return WebClient(token=tokens[teamId])


def errorMessageResp(errMsg, triggerKey):
    returnError = {
        "response_action": "errors",
        "errors": {}
    }
    returnError["errors"][triggerKey] = errMsg

    return returnError
