// The key screens, each opened as the demo person whose work it is, and what
// that person must see there. run.mjs opens them against the demo workspace
// (onedesk/one_demo). Every page of ours is here (tests/guards/test_browser.py).

export const SCREENS = [
	// One
	{ who: "samir@one.test", path: "/desk/one", sees: ["Today", "Tasks Due or Late", "Meetings Today"] },
	{ who: "wsadmin@one.test", path: "/desk/settings", page: "settings", sees: ["Profile", "Layla Haddad"] },
	{ who: "wsadmin@one.test", path: "/desk/workspace-settings", page: "workspace-settings", sees: ["Workspace"] },
	{ who: "wsadmin@one.test", path: "/desk/masters", page: "masters", sees: ["Masters"] },
	{ who: "wsadmin@one.test", path: "/desk/legal", page: "legal", sees: ["Terms of Service"] },
	// OneIntake, OneMail, OneCloud
	{ who: "wsadmin@one.test", path: "/desk/intake", page: "intake", sees: ["Taxi back from Bayview"] },
	{ who: "wsadmin@one.test", path: "/desk/onemail", page: "onemail", sees: ["Lobby glazing at Bayview Tower"] },
	{ who: "huda@one.test", path: "/desk/onecloud", page: "onecloud", sees: ["Bank Statements"] },
	{ who: "huda@one.test", path: "/desk/ready-to-submit", page: "ready-to-submit", sees: ["Ready to Submit"] },
	// OneProject, OneTask, OneCalendar
	{ who: "samir@one.test", path: "/desk/project", sees: ["Mansour Villa Windows and Doors", "Bayview Tower Curtain Wall"] },
	{ who: "samir@one.test", path: "/desk/project/PROJ-0001", page: "project-view", sees: ["Mansour Villa Windows and Doors", "Staircase balustrade"] },
	{ who: "samir@one.test", path: "/desk/project-template", sees: ["Aluminium & Glazing", "Tasks", "Days", "Projects", "From the Library"] },
	{ who: "samir@one.test", path: "/desk/project-template/Aluminium%20%26%20Glazing", page: "project-template-view", sees: ["Aluminium & Glazing", "Day 0"] },
	{ who: "rania@one.test", path: "/desk/my-tasks", page: "my-tasks", sees: ["OneTask"] },
	{ who: "samir@one.test", path: "/desk/onecalendar", page: "onecalendar", sees: ["Weekly site meeting"] },
	// OneCRM
	{ who: "omar@one.test", path: "/desk/onecrm", sees: ["OneCRM"] },
	{ who: "omar@one.test", path: "/desk/opportunity/view/kanban/Pipeline", sees: ["Webb Hotel lobby curtain wall"] },
	// OneBook, OneInventory
	{ who: "huda@one.test", path: "/desk/onebook", sees: ["OneBook"] },
	{ who: "karim@one.test", path: "/desk/item/ALU-6063", sees: ["ALU-6063"] },
	// OneHR
	{ who: "mariam@one.test", path: "/desk/onehr", sees: ["OneHR"] },
	// OneStudio
	{ who: "wsadmin@one.test", path: "/desk/extension", sees: ["Say When a Customer Has No Mobile"] },
	{ who: "wsadmin@one.test", path: "/desk/company-van", sees: ["D 41257"] },
];

// What no screen may say.
export const NEVER = ["Not Permitted", "Page Not Found", "Something went wrong", "Insufficient Permission"];
