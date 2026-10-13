import CTFd from "../index";
import Alpine from "alpinejs";

Alpine.data("LanguageForm", () => ({
  async set(event) {
    let language = event.target.getAttribute("value");
    const path = `${window.init.urlRoot || ""}/`;
    const secure = window.location.protocol === "https:" ? ";Secure" : "";
    document.cookie = `language=${language};Path=${path};SameSite=Lax${secure}`;

    // Set user language preference if logged in
    if (CTFd.user.id) {
      await CTFd.fetch("/api/v1/users/me", {
        method: "PATCH",
        body: JSON.stringify({ language }),
      });
    }

    // Reload with new language
    window.location.reload();
  },
}));
