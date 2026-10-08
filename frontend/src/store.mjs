import { ApiClient, ApiError, StaleSessionError } from "./lib/api.mjs";
import { validateFile, MIME } from "./lib/utils.mjs";

const fresh = () => ({
  authMode: "login",
  authBusy: false,
  authError: null,
  authEmail: "",
  patient: null,
  view: "overview",
  health: null,
  config: null,
  documents: [],
  docsBusy: false,
  docsLoaded: false,
  docsError: null,
  filenames: new Map(),
  filters: { search: "", type: "", status: "" },
  file: null,
  uploadType: "",
  uploadDate: "",
  uploadBusy: false,
  uploadError: null,
  messages: [],
  chatBusy: false,
  chatType: "",
  draft: "",
  dialog: null,
  deleteBusy: false,
  deleteError: null,
  toast: "",
});

export function createPortalStore({
  fetchImpl = globalThis.fetch.bind(globalThis),
  location = globalThis.location,
} = {}) {
  let state = fresh(),
    snapshot,
    revision = 0,
    docsRevision = 0,
    detailRevision = 0,
    bootRevision = 0,
    poll,
    toastTimer;
  const listeners = new Set();
  const api = new ApiClient({
    fetchImpl,
    onExpired: () => logout("Your session ended. Please sign in again."),
  });
  function publish() {
    snapshot = {
      ...state,
      documents: [...state.documents],
      messages: state.messages.map((m) => ({ ...m })),
      filenames: new Map(state.filenames),
      filters: { ...state.filters },
      dialog: state.dialog ? { ...state.dialog } : null,
    };
    listeners.forEach((fn) => fn());
  }
  publish();
  function notify(message) {
    clearTimeout(toastTimer);
    state.toast = message;
    publish();
    toastTimer = setTimeout(() => {
      state.toast = "";
      publish();
    }, 5000);
  }
  function closeDialog() {
    detailRevision++;
    state.dialog = null;
    state.deleteError = null;
    publish();
  }
  function navigate(view) {
    if (!state.patient) return;
    state.view = ["overview", "documents", "chat", "account"].includes(view)
      ? view
      : "overview";
    if (location) location.hash = state.view;
    publish();
  }
  function logout(message) {
    api.clearSession();
    revision++;
    docsRevision++;
    detailRevision++;
    bootRevision++;
    clearTimeout(poll);
    clearTimeout(toastTimer);
    state = fresh();
    state.authError = message ? { message } : null;
    if (location) location.hash = "";
    publish();
    bootstrap();
  }
  async function bootstrap() {
    const epoch = api.version,
      version = ++bootRevision;
    const results = await Promise.allSettled([
      api.request("/api/v1/ui/config", { auth: false, group: "bootstrap" }),
      api.request("/ready", { auth: false, group: "bootstrap" }),
    ]);
    if (epoch !== api.version || version !== bootRevision) return;
    state.config = results[0].status === "fulfilled" ? results[0].value : null;
    state.health = results[1].status === "fulfilled";
    publish();
  }
  async function loadDocs() {
    if (!state.patient || state.docsBusy) return;
    const epoch = api.version,
      version = ++docsRevision;
    state.docsBusy = true;
    state.docsError = null;
    publish();
    try {
      const data = await api.request("/api/v1/documents", {
        group: "documents",
      });
      if (epoch !== api.version || version !== docsRevision) return;
      if (!Array.isArray(data.documents))
        throw new ApiError(
          "The record list could not be read. Please try again.",
        );
      state.documents = data.documents;
      state.docsLoaded = true;
    } catch (error) {
      if (
        epoch === api.version &&
        version === docsRevision &&
        !(error instanceof StaleSessionError)
      )
        state.docsError = error;
    } finally {
      if (epoch === api.version && version === docsRevision) {
        state.docsBusy = false;
        publish();
        clearTimeout(poll);
        if (
          state.documents.some((d) =>
            ["uploaded", "processing"].includes(d.processing_status),
          )
        )
          poll = setTimeout(loadDocs, 10000);
      }
    }
  }
  async function authenticate({ name, email, password }) {
    if (state.authBusy) return;
    const registering = state.authMode === "register",
      epoch = api.version;
    let sessionEpoch = epoch,
      created = false;
    state.authEmail = email;
    state.authBusy = true;
    state.authError = null;
    publish();
    try {
      if (registering) {
        await api.request("/api/v1/auth/register", {
          auth: false,
          method: "POST",
          body: { name, email, password },
        });
        created = true;
      }
      const token = await api.request("/api/v1/auth/login", {
        auth: false,
        method: "POST",
        body: { email, password },
      });
      if (epoch !== api.version) return;
      api.setSession(token.access_token, token.expires_in);
      sessionEpoch = api.version;
      const patient = await api.request("/api/v1/auth/me");
      if (sessionEpoch !== api.version) return;
      state.patient = patient;
      state.authBusy = false;
      navigate("overview");
      bootstrap();
      loadDocs();
    } catch (error) {
      if (error instanceof StaleSessionError || sessionEpoch !== api.version)
        return;
      if (api.token) api.clearSession();
      state.authError = created
        ? { message: "Your account was created. Please sign in to continue." }
        : error;
      if (created) state.authMode = "login";
      state.authBusy = false;
      publish();
    } finally {
      password = "";
    }
  }
  function setFile(file) {
    const error = validateFile(file, state.config);
    state.file = error ? null : file;
    state.uploadError = error ? { message: error } : null;
    publish();
  }
  async function upload() {
    if (state.uploadBusy) return;
    const error = validateFile(state.file, state.config);
    if (error) {
      state.uploadError = { message: error };
      publish();
      return;
    }
    const epoch = api.version,
      original = state.file,
      extension = original.name.split(".").pop().toLowerCase();
    const file =
      original.type === MIME[extension]
        ? original
        : new File([original], original.name, { type: MIME[extension] });
    const body = new FormData();
    body.append("file", file);
    if (state.uploadType) body.append("document_type", state.uploadType);
    if (state.uploadDate) body.append("document_date", state.uploadDate);
    state.uploadBusy = true;
    state.uploadError = null;
    publish();
    try {
      const record = await api.request("/api/v1/documents/upload", {
        method: "POST",
        body,
        group: "upload",
        timeoutMs: 600000,
      });
      if (epoch !== api.version) return;
      state.filenames.set(record.document_id, original.name);
      state.file = null;
      state.uploadType = "";
      state.uploadDate = "";
      notify("Your record was added.");
    } catch (error) {
      if (epoch === api.version && !(error instanceof StaleSessionError))
        state.uploadError = error;
    } finally {
      if (epoch === api.version) {
        state.uploadBusy = false;
        publish();
        loadDocs();
      }
    }
  }
  function clearChat() {
    api.abortGroup("chat");
    revision++;
    state.messages = [];
    state.draft = "";
    state.chatBusy = false;
    publish();
  }
  async function ask(question = state.draft) {
    if (!state.patient || state.chatBusy) return;
    question = question.trim();
    if (!state.documents.some((d) => d.processing_status === "completed")) {
      navigate("documents");
      return;
    }
    if (
      !question ||
      question.length > (state.config?.question_max_length || 2000)
    )
      return;
    const epoch = api.version,
      version = revision,
      id = crypto.randomUUID(),
      started = performance.now();
    state.messages.push({ id, question, status: "pending" });
    state.chatBusy = true;
    state.draft = "";
    navigate("chat");
    try {
      const body = { question };
      if (state.chatType) body.document_type = state.chatType;
      const result = await api.request("/api/v1/chat/query", {
        method: "POST",
        body,
        group: "chat",
        timeoutMs: (state.config?.query_timeout_seconds || 180) * 1000 + 15000,
      });
      if (epoch !== api.version || version !== revision) return;
      if (
        typeof result.answer !== "string" ||
        !Array.isArray(result.sources) ||
        !["answered", "insufficient_context"].includes(result.status)
      )
        throw new ApiError(
          "The service returned an unreadable answer. Please try again.",
        );
      Object.assign(
        state.messages.find((m) => m.id === id),
        { status: "finished", result, elapsed: performance.now() - started },
      );
    } catch (error) {
      if (epoch !== api.version || version !== revision) return;
      Object.assign(
        state.messages.find((m) => m.id === id),
        { status: "error", error },
      );
    } finally {
      if (epoch === api.version && version === revision) {
        state.chatBusy = false;
        publish();
      }
    }
  }
  async function showRecord(id) {
    const epoch = api.version,
      version = ++detailRevision;
    state.dialog = { kind: "record", loading: true };
    publish();
    try {
      const record = await api.request(
        `/api/v1/documents/${encodeURIComponent(id)}`,
      );
      if (epoch === api.version && version === detailRevision && state.dialog) {
        state.dialog = { kind: "record", record };
        publish();
      }
    } catch (error) {
      if (epoch === api.version && version === detailRevision && state.dialog) {
        state.dialog = { kind: "record", error };
        publish();
      }
    }
  }
  function confirmDelete(id) {
    detailRevision++;
    state.dialog = { kind: "delete", id };
    state.deleteError = null;
    state.deleteBusy = false;
    publish();
  }
  async function deleteRecord() {
    if (!state.dialog || state.dialog.kind !== "delete" || state.deleteBusy)
      return;
    const id = state.dialog.id,
      epoch = api.version;
    state.deleteBusy = true;
    publish();
    try {
      await api.request(`/api/v1/documents/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      if (epoch !== api.version) return;
      state.filenames.delete(id);
      api.abortGroup("documents");
      docsRevision++;
      state.docsBusy = false;
      state.documents = state.documents.filter((d) => d.document_id !== id);
      closeDialog();
      clearChat();
      notify("Record deleted.");
      loadDocs();
    } catch (error) {
      if (epoch === api.version) {
        state.deleteError = error;
        publish();
      }
    } finally {
      if (epoch === api.version) {
        state.deleteBusy = false;
        publish();
      }
    }
  }
  const actions = {
    bootstrap,
    loadDocs,
    authenticate,
    logout,
    navigate,
    setFile,
    upload,
    ask,
    clearChat,
    showRecord,
    confirmDelete,
    deleteRecord,
    closeDialog,
    authMode(mode) {
      if (state.authBusy) return;
      state.authMode = mode;
      state.authError = null;
      publish();
    },
    set(field, value) {
      if (
        ![
          "authEmail",
          "draft",
          "chatType",
          "uploadType",
          "uploadDate",
        ].includes(field)
      )
        return;
      state[field] = value;
      publish();
    },
    filter(field, value) {
      if (!["search", "type", "status"].includes(field)) return;
      state.filters[field] = value;
      publish();
    },
    resetFilters() {
      state.filters = { search: "", type: "", status: "" };
      publish();
    },
    removeFile() {
      state.file = null;
      state.uploadError = null;
      publish();
    },
    rejectFiles() {
      state.uploadError = { message: "Choose one record at a time." };
      publish();
    },
    askRecordType(type) {
      state.chatType = type;
      closeDialog();
      navigate("chat");
    },
    retry(id) {
      const m = state.messages.find((m) => m.id === id);
      if (m) ask(m.question);
    },
    async copy(id) {
      const m = state.messages.find((m) => m.id === id);
      if (m?.result)
        try {
          await navigator.clipboard.writeText(m.result.answer);
          notify("Answer copied.");
        } catch {
          notify("Copy is unavailable. Select the answer text to copy it.");
        }
    },
  };
  function hashChange() {
    if (state.patient && location?.hash !== "#main")
      navigate(location?.hash.slice(1));
  }
  return {
    getSnapshot: () => snapshot,
    subscribe(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    actions,
    start() {
      globalThis.addEventListener?.("hashchange", hashChange);
      bootstrap();
      return () => {
        globalThis.removeEventListener?.("hashchange", hashChange);
        bootRevision++;
        api.abortGroup("bootstrap");
        clearTimeout(poll);
      };
    },
    dispose() {
      api.clearSession();
      revision++;
      docsRevision++;
      detailRevision++;
      bootRevision++;
      clearTimeout(poll);
      clearTimeout(toastTimer);
      state = fresh();
      publish();
      listeners.clear();
    },
  };
}
