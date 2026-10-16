import Alpine from "alpinejs";
import dayjs from "dayjs";

import CTFd from "./index";

import { Modal, Tab, Tooltip } from "bootstrap";
import highlight from "./theme/highlight";

function addTargetBlank(html) {
  let dom = new DOMParser();
  let view = dom.parseFromString(html, "text/html");
  let links = view.querySelectorAll('a[href*="://"]');
  links.forEach(link => {
    link.setAttribute("target", "_blank");
  });
  return view.documentElement.outerHTML;
}

window.Alpine = Alpine;

Alpine.store("challenge", {
  data: {
    view: "",
  },
});

Alpine.data("Hint", () => ({
  id: null,
  html: null,
  busy: false,
  error: "",

  async showHint(event) {
    if (event.target.open && !this.busy) {
      this.busy = true;
      this.error = "";
      try {
        let response = await CTFd.pages.challenge.loadHint(this.id);

        // Hint has some kind of prerequisite or access prevention
        if (response.errors) {
          event.target.open = false;
          CTFd._functions.challenge.displayUnlockError(response);
          return;
        }
        let hint = response.data;
        if (hint.content) {
          this.html = addTargetBlank(hint.html);
        } else {
          let answer =
            hint.cost === 0 || (await CTFd.pages.challenge.displayHintUnlock(hint));
          if (answer) {
            let unlock = await CTFd.pages.challenge.loadUnlock(this.id);

            if (unlock.success) {
              let response = await CTFd.pages.challenge.loadHint(this.id);
              let hint = response.data;
              this.html = addTargetBlank(hint.html);
            } else {
              event.target.open = false;
              CTFd._functions.challenge.displayUnlockError(unlock);
            }
          } else {
            event.target.open = false;
          }
        }
      } catch (_) {
        this.error = "The hint could not be loaded. Close and reopen it to try again.";
      } finally {
        this.busy = false;
      }
    }
  },
}));

Alpine.data("Challenge", () => ({
  id: null,
  next_id: null,
  submission: "",
  tab: null,
  solves: [],
  submissions: [],
  solution: null,
  response: null,
  submitting: false,
  submissionError: "",
  share_url: null,
  max_attempts: 0,
  attempts: 0,
  ratingValue: 0,
  selectedRating: 0,
  ratingReview: "",
  ratingSubmitted: false,
  ratingBusy: false,
  ratingError: "",

  async init() {
    highlight();
  },

  getStyles() {
    let styles = {
      "modal-dialog": true,
    };
    try {
      let size = CTFd.config.themeSettings.challenge_window_size;
      switch (size) {
        case "sm":
          styles["modal-sm"] = true;
          break;
        case "lg":
          styles["modal-lg"] = true;
          break;
        case "xl":
          styles["modal-xl"] = true;
          break;
        default:
          break;
      }
    } catch (error) {
      // Ignore errors with challenge window size
      console.log("Error processing challenge_window_size");
      console.log(error);
    }
    return styles;
  },

  async showChallenge() {
    new Tab(this.$el).show();
  },

  async showSolves() {
    this.solves = await CTFd.pages.challenge.loadSolves(this.id);
    this.solves.forEach(solve => {
      solve.date = dayjs(solve.date).format("MMMM Do, h:mm:ss A");
      return solve;
    });
    new Tab(this.$el).show();
  },

  async showSubmissions() {
    let response = await CTFd.pages.users.userSubmissions("me", this.id);
    this.submissions = response.data;
    this.submissions.forEach(s => {
      s.date = dayjs(s.date).format("MMMM Do, h:mm:ss A");
      return s;
    });
    new Tab(this.$el).show();
  },

  getSolutionId() {
    let data = Alpine.store("challenge").data;
    return data.solution_id;
  },

  getSolutionState() {
    let data = Alpine.store("challenge").data;
    return data.solution_state;
  },

  setSolutionId(solutionId) {
    Alpine.store("challenge").data.solution_id = solutionId;
  },

  async showSolution() {
    let solution_id = this.getSolutionId();
    CTFd._functions.challenge.displaySolution = solution => {
      this.solution = solution.html;
      new Tab(this.$el).show();
    };
    await CTFd.pages.challenge.displaySolution(solution_id);
  },

  getNextId() {
    let data = Alpine.store("challenge").data;
    return data.next_id;
  },

  async nextChallenge() {
    let modal = Modal.getOrCreateInstance("[x-ref='challengeWindow']");

    // TODO: Get rid of this private attribute access
    // See https://github.com/twbs/bootstrap/issues/31266
    modal._element.addEventListener(
      "hidden.bs.modal",
      event => {
        // Dispatch load-challenge event to call loadChallenge in the ChallengeBoard
        Alpine.nextTick(() => {
          this.$dispatch("load-challenge", this.getNextId());
        });
      },
      { once: true },
    );
    modal.hide();
  },

  async getShareUrl() {
    let body = {
      type: "solve",
      challenge_id: this.id,
    };
    const response = await CTFd.fetch("/api/v1/shares", {
      method: "POST",
      body: JSON.stringify(body),
    });
    const data = await response.json();
    const url = data["data"]["url"];
    this.share_url = url;
  },

  copyShareUrl() {
    navigator.clipboard.writeText(this.share_url);
    let t = Tooltip.getOrCreateInstance(this.$el);
    t.enable();
    t.show();
    setTimeout(() => {
      t.hide();
      t.disable();
    }, 2000);
  },

  async submitChallenge() {
    if (this.submitting || !this.submission.trim()) return;
    this.submitting = true;
    this.submissionError = "";
    try {
      const response = await CTFd.pages.challenge.submitChallenge(
        this.id,
        this.submission,
      );
      if (!response?.data?.status) throw new Error("Submission failed");
      this.response = response;
      await this.renderSubmissionResponse();
    } catch (error) {
      this.submissionError =
        "Your submission could not be completed. Please try again.";
    } finally {
      this.submitting = false;
    }
  },

  async renderSubmissionResponse() {
    if (this.response.data.status === "correct") {
      this.submission = "";
    }
    if (["correct", "already_solved"].includes(this.response.data.status)) {
      this.$dispatch("challenge-completed", {
        id: this.id,
        preview: this.response.data.preview === true,
      });
    }

    // Decide whether to check for the solution
    if (this.getSolutionId() == null) {
      if (
        CTFd.pages.challenge.checkSolution(
          this.getSolutionState(),
          Alpine.store("challenge").data,
          this.response.data.status,
        )
      ) {
        let data = await CTFd.pages.challenge.getSolution(this.id);
        this.setSolutionId(data.id);
      }
    }

    // Increment attempts counter
    if (
      this.max_attempts > 0 &&
      this.response.data.status != "already_solved" &&
      this.response.data.status != "ratelimited"
    ) {
      this.attempts += 1;
    }

    // Dispatch load-challenges event to call loadChallenges in the ChallengeBoard
    this.$dispatch("load-challenges");
  },

  async submitRating() {
    if (this.ratingBusy || ![1, -1].includes(this.selectedRating)) return;
    this.ratingBusy = true;
    this.ratingError = "";
    try {
      const response = await CTFd.pages.challenge.submitRating(
        this.id,
        this.selectedRating,
        this.ratingReview,
      );
      if (!response?.value) throw new Error("Rating failed");
      this.ratingValue = this.selectedRating;
      this.ratingSubmitted = true;
    } catch (_) {
      this.ratingError = "Your rating could not be saved. Please try again.";
      this.selectedRating = this.ratingValue || 0;
    } finally {
      this.ratingBusy = false;
    }
  },
}));

Alpine.data("ChallengeBoard", () => ({
  loaded: false,
  challenges: [],
  challenge: null,
  opening: false,
  previewSolves: [],

  async init() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(this.previewKey()) || "[]");
      this.previewSolves = Array.isArray(saved) ? saved.filter(id => typeof id === "string") : [];
    } catch (_) {
      this.previewSolves = [];
    }
    await this.loadChallenges();
    this.loaded = true;

    if (window.location.hash) {
      let chalHash = decodeURIComponent(window.location.hash.substring(1));
      let idx = chalHash.lastIndexOf("-");
      if (idx >= 0) {
        let pieces = [chalHash.slice(0, idx), chalHash.slice(idx + 1)];
        let id = pieces[1];
        await this.loadChallenge(id);
      }
    }
  },

  getCategories() {
    const categories = [];

    this.challenges.forEach(challenge => {
      const { category } = challenge;

      if (!categories.includes(category)) {
        categories.push(category);
      }
    });

    try {
      const f = CTFd.config.themeSettings.challenge_category_order;
      if (f) {
        const getSort = new Function(`return (${f})`);
        categories.sort(getSort());
      }
    } catch (error) {
      // Ignore errors with theme category sorting
      console.log("Error running challenge_category_order function");
      console.log(error);
    }

    return categories;
  },

  getChallenges(category) {
    let challenges = this.challenges;

    if (category !== null) {
      challenges = this.challenges.filter(challenge => challenge.category === category);
    }

    try {
      const f = CTFd.config.themeSettings.challenge_order;
      if (f) {
        const getSort = new Function(`return (${f})`);
        challenges.sort(getSort());
      }
    } catch (error) {
      // Ignore errors with theme challenge sorting
      console.log("Error running challenge_order function");
      console.log(error);
    }

    return challenges;
  },

  async loadChallenges() {
    const challenges = await CTFd.pages.challenges.getChallenges();
    this.challenges = challenges.map(challenge => ({
      ...challenge,
      preview_solved: challenge.state === "hidden" && this.previewSolves.includes(String(challenge.id)),
    }));
  },

  previewKey() {
    return `cyberdune-preview-solves:${window.init.userId}`;
  },

  markCompleted({ id, preview }) {
    const challenge = this.challenges.find(item => String(item.id) === String(id));
    if (!challenge) return;
    if (preview) {
      challenge.preview_solved = true;
      if (!this.previewSolves.includes(String(id))) this.previewSolves.push(String(id));
      try {
        sessionStorage.setItem(this.previewKey(), JSON.stringify(this.previewSolves));
      } catch (_) {
        // Preview feedback still works when browser storage is unavailable.
      }
    } else {
      challenge.solved_by_me = true;
    }
  },

  async loadChallenge(challengeId) {
    if (this.opening) return;
    this.opening = true;
    try {
      await CTFd.pages.challenge.displayChallenge(challengeId, challenge => {
        challenge.data.view = addTargetBlank(challenge.data.view);
        Alpine.store("challenge").data = challenge.data;

        // nextTick is required here because we're working in a callback
        Alpine.nextTick(() => {
          let modal = Modal.getOrCreateInstance("[x-ref='challengeWindow']");
          // TODO: Get rid of this private attribute access
          // See https://github.com/twbs/bootstrap/issues/31266
          modal._element.addEventListener(
            "hidden.bs.modal",
            event => {
              // Remove location hash
              history.replaceState(null, null, " ");
            },
            { once: true },
          );
          modal.show();
          history.replaceState(null, null, `#${challenge.data.name}-${challengeId}`);
        });
      });
    } finally {
      this.opening = false;
    }
  },
}));

Alpine.start();
