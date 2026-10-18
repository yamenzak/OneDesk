export function money(value, said) {
  const fixed = (Number(value) || 0).toFixed(said.precision);
  const [whole, part] = fixed.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, said.group);
  const number = part ? `${grouped}${said.decimal}${part}` : grouped;
  return said.on_right ? `${number} ${said.symbol}` : `${said.symbol} ${number}`;
}
