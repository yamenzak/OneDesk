"""What OneAI does in OneChat: nothing of its own. A conversation is people's
own words, and an agent takes part in it by being asked there
(answers.py), never by writing into it from elsewhere.
"""

# What OneAI does for every call here that changes something
# (docs/READY.md, mechanism 11): none is a card of its own, each for the
# reason given.
REACH = {}

NOT_FOR_AI = {
	"api.send": "A message is somebody's own words, written by them in the conversation.",
	"api.react": "A reaction is somebody's own, given on the message.",
	"api.make": "A channel is made by the person who will talk in it.",
	"api.direct": "A direct conversation is opened by one of the two people in it.",
	"api.talk": "A conversation with an agent is opened by the person who talks to it.",
	"api.join": "A person joins a channel themselves.",
	"api.add": "People are added to a channel by somebody in it.",
	"api.leave": "A person leaves a channel themselves.",
	"api.approve": "A card is the agent asking a person; only that person answers it.",
	"api.dismiss": "A card is the agent asking a person; only that person answers it.",
	"api.change": "A card is the agent asking a person; only that person changes it.",
	"api.keep": "A card is the agent asking a person; only that person keeps what the auditor doubted.",
	"api.undo": "A card is the agent asking a person; only that person takes it back.",
	"panel.start": "A conversation with an agent is opened by the person who talks to it.",
	"panel.say": "It is the person asking the agent, in the panel.",
	"panel.rename": "A conversation is named by the person it belongs to.",
	"api.seen": "It marks what the reader has read, as they open a conversation.",
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneChat's screen."""
	if said.get("page") == "onechat":
		return (
			"The reader is in OneChat, which lists their channels, direct messages and conversations with agents, "
			"with one conversation open. What people wrote there is not sent; how OneChat works is in its "
			"documentation (how_to)."
		)
	return None

