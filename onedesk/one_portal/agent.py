"""What OneAI does in OnePortal (docs/READY.md, mechanism 11): nothing yet.
Everything here either opens the workspace to somebody outside it, which a
person in the workspace decides, or is that outsider's own answer on the
portal, which nobody gives for them."""

REACH = {}


NOT_FOR_AI = {
	"invite.invite_contact": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"invite.invite_again": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"invite.restore": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"invite.revoke": "Turning a person's access off signs them out at once, so a person in the workspace decides it.",
	"share.set_access": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"share.make_link": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"share.mail_link": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"share.rotate_link": "It opens the workspace's records to somebody outside it, so a person in the workspace decides it.",
	"share.revoke_link": "Turning a link off stops it at once for whoever holds it, so a person in the workspace decides it.",
	"share.link_view": "Opening a link counts as the visit of whoever holds it, so only they open it.",
	"share.link_accept": "It is a customer's or supplier's own answer on the portal, which nobody in the workspace gives for them.",
	"share.link_decline": "It is a customer's or supplier's own answer on the portal, which nobody in the workspace gives for them.",
	"share.link_preview": "It reckons a quote as the supplier types it, on their own page.",
	"share.link_send": "It is a customer's or supplier's own answer on the portal, which nobody in the workspace gives for them.",
}
