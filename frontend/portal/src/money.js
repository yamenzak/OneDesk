// Money written as the workspace writes it, for a figure the reader is still
// typing (a quote's amounts): the separators, precision and symbol the server
// sends with the page (one/portal.py `rfq`).
export function money(value, said) {
  const fixed = (Number(value) || 0).toFixed(said.precision);
  const [whole, part] = fixed.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, said.group);
  const number = part ? `${grouped}${said.decimal}${part}` : grouped;
  return said.on_right ? `${number} ${said.symbol}` : `${said.symbol} ${number}`;
}
