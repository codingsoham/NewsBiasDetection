# Annotation Guidelines: Political Framing in Indian English News

## Task Description
Label each Indian English political news article according to the **leaning of its framing**, regardless of personal agreement or ideological preference.

---

## Labels

### 1. `LEFT`
Framing is critical of the ruling government or of majority-religion-based politics, or sympathetic to opposition parties, minority and civil-liberties concerns, secular-liberal positions, or welfare-state and redistributive policies.

* **Typical cues:**
  * Government actions described as failures, overreach, or threats to institutions.
  * Opposition figures and civil society critics quoted favorably or given the central voice.
  * Focus on democratic backsliding, inequality, or civil rights concerns.

---

### 2. `RIGHT`
Framing is supportive of the ruling government, Hindu-nationalist or cultural-nationalist positions, market-oriented/strong-state positions, or critical of opposition parties, "pseudo-secularism", or liberal critics.

* **Typical cues:**
  * Government actions characterized as major achievements, decisive leadership, or national progress.
  * Opposition parties described as obstructive, corrupt, or anti-national.
  * Official statements or government claims presented uncritically as established fact.

---

### 3. `CENTER`
Neutral, descriptive, or balanced reporting.

* **Typical cues:**
  * Facts are directly attributed to sources.
  * Multiple perspectives are given comparable space and weight.
  * Minimal use of evaluative, emotive, or loaded language.
  * Routine coverage (e.g., procedural court orders, official data releases, logistical event announcements).

---

### 4. `UNCLEAR / NOT_POLITICAL`
The text is non-political, ambiguous, or lacks sufficient substance to evaluate. *(Note: These records are excluded from training datasets).*

* **Typical cues:**
  * Routine coverage of sports, purely financial/business updates, lifestyle, entertainment, or local crime without political implications.
  * Snippets, headlines without text, or ambiguous summaries where framing cannot be determined.

---

## Annotation Rules & Edge Cases

1. **Focus on the text, not the publication:** Base judgments solely on word choice, emphasis, and quote selection within the article—not on the outlet's historical reputation.
2. **Genre distinction:** 
   * **Opinion pieces & Editorials:** Label by the explicit thesis and core argument.
   * **News reports:** Label by structural framing, headline tone, and source balance.
3. **Attribution vs. Endorsement:** Quoting a partisan figure is standard reporting. Bias occurs when a partisan claim is presented as undisputed objective fact.
4. **Tie-breaking standard:** When in doubt between a partisan label and `CENTER`, choose **`CENTER`** unless evaluative framing or clear slant is evident.
5. **Non-political default:** Stories focused solely on business, entertainment, crime, or sports without political framing must be labeled **`UNCLEAR / NOT_POLITICAL`**.