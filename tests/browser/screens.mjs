// The key screens, each opened as the demo person whose work it is, and what
// that person must see there. run.mjs opens them against the demo workspace
// (onedesk/one_demo). Every page of ours is here (tests/guards/test_browser.py).

// OneProject's places: its panel's rows, and its breadcrumb menu on a phone
// and over a record.
const PROJECT_PLACES = ["Projects", "Workload", "Timesheet", "Templates"];

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
	{ who: "samir@one.test", path: "/desk/project", sees: ["Mansour Villa Windows and Doors", "Bayview Tower Curtain Wall"], panel: true, phone: PROJECT_PLACES },
	{ who: "samir@one.test", path: "/desk/project/view/kanban/Projects%20by%20Health", sees: ["Mansour Villa Windows and Doors"], panel: true, phone: PROJECT_PLACES },
	{ who: "samir@one.test", path: "/desk/query-report/Workload", sees: ["Workload", "Samir Aoun"], panel: true, phone: PROJECT_PLACES },
	{ who: "samir@one.test", path: "/desk/project/PROJ-0001", page: "project-view", sees: ["Mansour Villa Windows and Doors", "Staircase balustrade", "Assign", "Files"], panel: false, menu: PROJECT_PLACES, trail: ["Projects", "Mansour Villa Windows and Doors", "All Work"] },
	{ who: "samir@one.test", path: "/desk/project/PROJ-0001?view=activity", page: "project-view", sees: ["Comment", "New Email", "Assign"], panel: false },
	{ who: "samir@one.test", path: "/desk/project-template", sees: ["Aluminium & Glazing", "Tasks", "Days", "Projects", "From the Library"], panel: true, phone: PROJECT_PLACES },
	{ who: "samir@one.test", path: "/desk/project-template/Aluminium%20%26%20Glazing", page: "project-template-view", sees: ["Aluminium & Glazing", "Day 0", "Assign", "Files"], panel: false, menu: PROJECT_PLACES },
	{ who: "samir@one.test", path: "/desk/task/TASK-2026-00052", page: "task-view", sees: ["Install glass", "Assign", "Files"], panel: false },
	{ who: "rania@one.test", path: "/desk/my-tasks", page: "my-tasks", sees: ["OneTask"] },
	{ who: "rania@one.test", path: "/desk/timers", page: "timers", sees: ["Timers"] },
	{ who: "samir@one.test", path: "/desk/onecalendar", page: "onecalendar", sees: ["Weekly site meeting"] },
	// OneInventory
	{ who: "karim@one.test", path: "/desk/stock-on-hand", page: "stock-on-hand", sees: ["Stock on Hand", "Structural Silicone", "All Warehouses"], panel: true },
	{ who: "karim@one.test", path: "/desk/item/ALU-6063", page: "item-view", sees: ["Aluminium Profile 6063", "On Hand", "Al Noor Aluminium", "Assign", "Files"], panel: false },
	{ who: "tariq@one.test", path: "/desk/item/WIN-CS12?view=making", page: "item-view", sees: ["Casement Window 1200", "Made From", "Being Made"], panel: false },
	{ who: "omar@one.test", path: "/desk/onecrm", page: "onecrm", sees: ["Pipeline Value", "Sales Trend", "Funnel Conversion"], panel: true },
	{ who: "omar@one.test", path: "/desk/onecrm?view=today", page: "onecrm", sees: ["Opportunities Due", "Unclaimed Leads"], panel: true },
	{ who: "omar@one.test", path: "/desk/onecrm/setup", page: "onecrm", sees: ["Sales Stage", "The stages an opportunity moves through, and their probability."], panel: true },
	{ who: "mariam@one.test", path: "/desk/onehr", page: "onehr", sees: ["Headcount", "Headcount by Department", "Payroll"], panel: true },
	{ who: "mariam@one.test", path: "/desk/onehr?view=today", page: "onehr", sees: ["Waiting for You", "Check-ins Flagged"], panel: true },
	{ who: "nadia@one.test", path: "/desk/onehr", page: "onehr", sees: ["Your Requests", "Privilege Leave Left"], panel: true },
	{ who: "huda@one.test", path: "/desk/books", page: "books", sees: ["Accounts Receivable", "Cash Flow", "Top Expenses"], panel: true },
	{ who: "huda@one.test", path: "/desk/books?view=today", page: "books", sees: ["Overdue", "Acme Holdings"], panel: true },
	{ who: "huda@one.test", path: "/desk/books/setup", page: "books", sees: ["Chart of Accounts", "The accounts the books are kept in."], panel: true },
	{ who: "karim@one.test", path: "/desk/inventory", page: "inventory", sees: ["Stock Worth", "3 Late Orders", "Where Stock Is", "Where Goods Came From and Went"], panel: true },
	{ who: "karim@one.test", path: "/desk/inventory?view=today", page: "inventory", sees: ["Late Orders", "Gulf Glass Industries"], panel: true },
	{ who: "karim@one.test", path: "/desk/inventory/setup", page: "inventory", sees: ["Warehouses", "Where stock is kept."], panel: true },
	{ who: "karim@one.test", path: "/desk/to-order", page: "to-order", sees: ["Running Low", "Structural Silicone Sealant"], panel: true },
	{ who: "karim@one.test", path: "/desk/lots", page: "lots", sees: ["Lots in Stock", "Weatherproof Silicone Sealant", "Stores - SGA"], panel: true },
	{ who: "karim@one.test", path: "/desk/quotes", page: "quotes", sees: ["Waiting for Prices", "Aluminium Profile 6063", "Euro Hardware Trading"], panel: true },
	{ who: "karim@one.test", path: "/desk/quotes?view=compare&request=PUR-RFQ-2026-00005", page: "quotes", sees: ["Cheapest", "Emirates Sealants & Fixings"], panel: true },
	{ who: "karim@one.test", path: "/desk/sent-out", page: "sent-out", sees: ["With Suppliers", "Gulf Powder Coating", "Aluminium Profile 6063, Powder Coated"], panel: true },
	{ who: "karim@one.test", path: "/desk/upkeep", page: "upkeep", sees: ["Due This Week", "Pickup Truck 2", "Yousef Bakr"], panel: true },
	{ who: "karim@one.test", path: "/desk/upkeep?view=repairs", page: "upkeep", sees: ["Laptop Huda", "Out of Order"], panel: true },
	{ who: "karim@one.test", path: "/desk/lots?view=serials", page: "lots", sees: ["SL-0001", "Smart Lock 500"], panel: true },
	{ who: "tariq@one.test", path: "/desk/plant", page: "plant", sees: ["Plant Floor", "Saw Line", "Glazing Table"], panel: true },
	{ who: "tariq@one.test", path: "/desk/floor", page: "floor", sees: ["Shop Floor", "Open Work Orders", "Sliding Door 2400"], panel: true },
	// OneCRM
	{ who: "omar@one.test", path: "/desk/onecrm", sees: ["OneCRM"] },
	{ who: "omar@one.test", path: "/desk/opportunity/view/kanban/Pipeline", sees: ["Webb Hotel lobby curtain wall"] },
	// OneBook, OneInventory
	{ who: "huda@one.test", path: "/desk/onebook", sees: ["OneBook"] },
	{ who: "karim@one.test", path: "/desk/item/ALU-6063", sees: ["ALU-6063"], trail: ["Items", "Raw Material", "Aluminium Profile 6063"] },
	// OneHR
	{ who: "mariam@one.test", path: "/desk/onehr", sees: ["OneHR"] },
	// OneStudio
	{ who: "wsadmin@one.test", path: "/desk/extension", sees: ["Say When a Customer Has No Mobile"] },
	{ who: "wsadmin@one.test", path: "/desk/company-van", sees: ["D 41257"] },
];

// What no screen may say.
export const NEVER = ["Not Permitted", "Page Not Found", "Something went wrong", "Insufficient Permission"];
