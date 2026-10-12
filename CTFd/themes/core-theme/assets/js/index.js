import CTFd from "@ctfdio/ctfd-js";

import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

import times from "./theme/times";
import styles from "./theme/styles";
import highlight from "./theme/highlight";

import alerts from "./utils/alerts";
import tooltips from "./utils/tooltips";
import collapse from "./utils/collapse";

import eventAlerts from "./utils/notifications/alerts";
import eventToasts from "./utils/notifications/toasts";
import eventRead from "./utils/notifications/read";

import "./components/language";

dayjs.extend(advancedFormat);
// The SSE endpoint requires authentication; guest pages should not reconnect to a 403.
const initEvents = CTFd.events.init;
CTFd.events.init = (...args) => {
  if (!window.init.userId) return;
  if (CTFd.events.source) CTFd.events.disconnect();
  initEvents(...args);
};
const connectEvents = CTFd.events.connect;
CTFd.events.connect = () => {
  if (CTFd.events.source) connectEvents();
};
CTFd.init(window.init);

(() => {
  styles();
  times();
  highlight();

  alerts();
  tooltips();
  collapse();

  eventRead();
  eventAlerts();
  eventToasts();
})();

export default CTFd;
