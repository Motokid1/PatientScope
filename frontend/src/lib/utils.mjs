export const TYPES = {
  prescription: "Prescription",
  lab_report: "Lab report",
  clinical_note: "Clinical note",
  claim_document: "Claim document",
  diagnostic_report: "Diagnostic report",
  discharge_summary: "Discharge summary",
  other: "Other record",
};
export const MIME = {
  pdf: "application/pdf",
  txt: "text/plain",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};
export function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );
}
export function dateLabel(value, fallback = "No record date") {
  if (!value) return fallback;
  const date = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime())
    ? fallback
    : new Intl.DateTimeFormat("en", {
        day: "numeric",
        month: "short",
        year: "numeric",
      }).format(date);
}
export function recordTitle(record, filenames = new Map()) {
  return (
    filenames.get(record.document_id) ||
    `${TYPES[record.document_type] || "Medical record"}${record.document_date ? ` · ${dateLabel(record.document_date)}` : ""}`
  );
}
export function validateFile(file, config) {
  if (!file) return "Choose a file to upload.";
  if (!config)
    return "Upload settings are unavailable. Please refresh the service status.";
  const extension = file.name.split(".").pop().toLowerCase();
  if (!config.supported_extensions.includes(extension))
    return "Choose a PDF, TXT, or DOCX file.";
  if (file.size === 0)
    return "This file is empty. Choose a file containing your record.";
  if (file.size > config.max_upload_size_mb * 1024 * 1024)
    return `Choose a file smaller than ${config.max_upload_size_mb} MB.`;
  if (
    file.type &&
    file.type !== "application/octet-stream" &&
    file.type !== MIME[extension]
  )
    return "The file format doesn't match its extension. Choose the original PDF, TXT, or DOCX.";
  return "";
}
export function filterRecords(
  records,
  { search = "", type = "", status = "" },
  filenames = new Map(),
) {
  const term = search.trim().toLocaleLowerCase();
  return records
    .filter(
      (record) =>
        (!type || record.document_type === type) &&
        (!status || record.processing_status === status) &&
        (!term ||
          `${recordTitle(record, filenames)} ${record.filename} ${TYPES[record.document_type]} ${dateLabel(record.document_date)}`
            .toLocaleLowerCase()
            .includes(term)),
    )
    .sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
}
export function formatBytes(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
