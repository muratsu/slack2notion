This doc is just for informational purposes, please visit the actual page [here](https://api.slack.com/tutorials/intro-to-modals-block-kit).

# Introduction

If you're learning about Slack apps, modals or slash commands for the first time, you've come to the right place! This tutorial will go through setting up your very own server using Glitch and have that server be the backend to your very own Slack app. Let's take a look through the technologies that we'll use in this tutorial.

### Glitch

Glitch is a online IDE (Integrated Development Environment) where you can collaboratively work on code and host your very own server. The second point is really important as it is a quick way to get up and running, without having to deal with figuring out which hosting solution you want for your app. Just as a note, Glitch should only be used for development purposes and should not be used in production.

### Python and Flask 🐍

Python is a programming language known for being easy to read and popular among beginner coders. We'll use this in conjunction with Flask, which is a web framework that'll allow us to create endpoints that our app will interact with.

### Block Kit

[Block Kit](https://api.slack.com/block-kit) is a UI framework for Slack apps that allows you to have beautiful, interactive messages within Slack. If you've ever seen a message in Slack with buttons or a select menu, that's Block Kit.

### Modals

[Modals](https://api.slack.com/surfaces/modals/using) are similar to a pop up that happen right in Slack. They grab the attention of the user and usually ask them to provide some kind of information or input.

---

# Steps

1. Create a new app by clicking [here](https://api.slack.com/apps/new), you're free to name it whatever you like.

2. Head over to this [Glitch project](https://glitch.com/~intro-to-modals) and hit `Remix Your Own` in the bottom right corner. This will clone the project and bring up your very own server! Most of the magic happens in the `server.py` file and `modal.txt` is where your Block Kit modal lives. Feel free to change things up and play around!


    Also, here's a copy of what the modal payload looks like, this is what powers the modal.

    ```
    {
    	"type": "modal",
    	"title": {
    		"type": "plain_text",
    		"text": "Gratitude Box",
    		"emoji": true
    	},
    	"submit": {
    		"type": "plain_text",
    		"text": "Submit",
    		"emoji": true
    	},
    	"close": {
    		"type": "plain_text",
    		"text": "Cancel",
    		"emoji": true
    	},
    	"blocks": [
    		{
    			"type": "input",
    			"block_id": "my_block",
    			"element": {
    				"type": "plain_text_input",
    				"action_id": "my_action"
    			},
    			"label": {
    				"type": "plain_text",
    				"text": "Say something nice!",
    				"emoji": true
    			}
    		}
    	]
    }
    ```

3. Find the base path to your server by clicking the "Share", then "Live App" buttons and copying the first link.


4. Head back to your app page and navigate to **Interactivity & Shortcuts** and paste that base path URL you just saved and add "/interactive" after it. e.g. `https://festive-harmonious-march.glitch.me/interactive`. This allows for your server to retrieve information from the modal. You can see the code for this within the Glitch project under Step 4.


5. Next, we're going to create the Slash Command so you can access it within Slack. Head over to the **Slash Commands** section in the left sidebar and create a new command. Note the **Request URL** is your base server link + "/slashcommand" after it. The code that powers the slash command and opens up a modal can be found within the Glitch project under Step 5.

6. Navigate to **Install App** and install.

7. After you've done this, you'll see a **Bot User OAuth Access Token**, copy this.

8. Head back to your Glitch project and click on the little heart and key.env file and paste your bot token where the TOKEN variable is shown. This allows your server to send authenticated requests to the Slack API.

9. Now that everything is set up, let's test by heading to Slack and typing `/thankyou`.

All done! 🎉 You've created your first Slash Command using Block Kit and Modals! The world is your oyster, you can create more and more complex modals by playing around first with the [Block Kit Builder](https://app.slack.com/block-kit-builder) and if you have any questions please feel free to reach out to developer support at feedback@slack.com.

# Extra Credit!

How to getting the lovely feedback in channel somewhere. This part isn't required but it's nice to have so that you can actually see the feedback people are giving each other somewhere.

1. Add the [`chat:write`](https://api.slack.com/scopes/chat:write) bot scope, this allows for your bot to post messages within Slack. You can do this in the **OAuth & Permissions** section on your Slack app.

2. Reinstall your app to make sure the scopes are applied.

3. Create a channel and name it `#thanks`. Next, get it's ID by right clicking on the channel name, copying the link and taking the last section that starts with the letter `C`. As an example, if your channel link looks like this, https://my.slack.com/archives/C123FCN2MLM, then the ID is `C123FCN2MLM`.

4. Add your bot to the channel by typing the command `/invite @your_bots_name`.

5. Uncomment the `Extra Credit` code within your glitch and make sure to replace `your_channel_id` with the ID in step 2.

6. Test it out by typing `/thankyou` and watch all the feedback come into your channel!
