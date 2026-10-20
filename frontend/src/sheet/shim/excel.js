// A formula as modern Excel saves it, as the editor reads it: the `_xlfn.`
// and `_xlws.` markers Excel puts before newer functions dropped, and the
// dotted names it added mapped to the classic ones the editor knows.
const CLASSIC = {
	"CEILING.MATH": "CEILING",
	"CEILING.PRECISE": "CEILING",
	"FLOOR.MATH": "FLOOR",
	"FLOOR.PRECISE": "FLOOR",
	"STDEV.S": "STDEV",
	"STDEV.P": "STDEVP",
	"VAR.S": "VAR",
	"VAR.P": "VARP",
	"PERCENTILE.INC": "PERCENTILE",
};

export function plainFormula(formula) {
	let said = String(formula).replace(/_xl(fn|ws)\./gi, "");
	for (const [dotted, classic] of Object.entries(CLASSIC)) {
		said = said.replace(new RegExp(`\\b${dotted.replace(".", "\\.")}\\s*\\(`, "gi"), `${classic}(`);
	}
	return said;
}
