// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/utils/format.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
export function formatSize(size, nDigits = 1) {
  if (size === 0) return 'empty'
  var i = -1
  var byteUnits = ['KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  do {
    size /= 1000
    i++
  } while (size > 1000)
  return Math.max(size, 0.1).toFixed(nDigits) + ' ' + byteUnits[i]
}

// One: the workspace's date and time formats in the reader's time zone, as frappe.datetime prints them
export function formatDate(date) {
  if (!date) return ''
  const { datetime } = window.frappe
  const when = datetime.convert_to_user_tz(typeof date === 'string' ? date : new Date(date), false)
  return `${when.format(datetime.get_user_date_fmt().toUpperCase())}, ${when.format(datetime.get_user_time_fmt())}`
}
