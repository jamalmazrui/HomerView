"""Submit the form the user is filling in, from whatever field they are in.

requestSubmit rather than submit, and this is the whole point of the module.
form.submit bypasses the form's own validation and never fires its submit
event, so a page that checks its fields in script would never see the attempt
and a required field left empty would be sent anyway. form.requestSubmit does
what pressing the submit button does: it validates, it fires the event, and it
refuses an incomplete form while showing the same message the user would have
seen. An error about a missing field is the correct outcome, not a failure.

A submitter is passed only when it is certain -- the button in focus, or the form's
only one -- because a form can have several submit buttons that mean different
things. With several and none in focus, nothing is sent and their names are said.
"""

from .logger import abbreviate, homerLog, logSection

submitTimeoutSeconds = 20.0

submitScript = r"""(() => {
    let el = document.activeElement;
    // Reach through a shadow root, which is where a form field often lives on
    // a modern site.
    while (el && el.shadowRoot && el.shadowRoot.activeElement) {
        el = el.shadowRoot.activeElement;
    }
    if (!el) return {outcome: "noForm"};
    const sSubmitters = 'button[type=submit], input[type=submit], button:not([type])';
    const labelOf = (e) => (e.innerText || e.value || e.getAttribute("aria-label") || "").trim().slice(0, 80);
    // NEVER A GUESSED BUTTON (30 October 2026, from an audit by another AI). The first
    // submit button was used, and outside a form element the first submit-like button
    // anywhere in the page was clicked: on a form with Save Draft and Send, or a page with
    // an unrelated button, that could be the wrong action. Now the button in focus is
    // used; otherwise only a button that is the one way to send the form; and when there
    // are several, nothing is sent and their names are said.
    const bIsSubmitter = el.matches && el.matches(sSubmitters);
    const elForm = el.form || (el.closest ? el.closest("form") : null);
    if (!elForm) {
        // A form built without a form element: only inside a container marked as a form,
        // and only when it holds exactly one submit-like button.
        const elRegion = el.closest ? el.closest("[role=form]") : null;
        if (!elRegion) return {outcome: "noForm"};
        const lButtons = Array.from(elRegion.querySelectorAll(sSubmitters + ', [role=button][data-submit]'));
        if (lButtons.length === 1) {
            lButtons[0].click();
            return {outcome: "submitted", how: "clicked the form region's only submit button", label: labelOf(lButtons[0])};
        }
        if (lButtons.length > 1) return {outcome: "ambiguous", labels: lButtons.map(labelOf).slice(0, 6)};
        return {outcome: "noForm"};
    }
    const lSubmitters = Array.from(elForm.querySelectorAll(sSubmitters))
        .concat(elForm.id ? Array.from(document.querySelectorAll(
            'button[form="' + elForm.id + '"], input[type=submit][form="' + elForm.id + '"]')) : []);
    let elSubmitter = null;
    if (bIsSubmitter && lSubmitters.includes(el)) elSubmitter = el;
    else if (lSubmitters.length === 1) elSubmitter = lSubmitters[0];
    else if (lSubmitters.length > 1) return {outcome: "ambiguous", labels: lSubmitters.map(labelOf).slice(0, 6)};
    const sLabel = elSubmitter ? labelOf(elSubmitter) : "";
    if (typeof elForm.requestSubmit === "function") {
        if (!elForm.checkValidity || !elForm.checkValidity()) {
            // Let the browser show its own message, exactly as it would if the
            // submit button had been pressed.
            elForm.requestSubmit(elSubmitter || undefined);
            return {outcome: "invalid", label: sLabel};
        }
        elForm.requestSubmit(elSubmitter || undefined);
        return {outcome: "submitted", how: "requestSubmit", label: sLabel};
    }
    if (elSubmitter) {
        elSubmitter.click();
        return {outcome: "submitted", how: "clicked the submit button", label: sLabel};
    }
    elForm.submit();
    return {outcome: "submitted", how: "form.submit, without validation", label: sLabel};
})()"""


def submitFocusedForm(cdpSession):
    logSection("Command: submit the form")
    dTarget, sSessionId = cdpSession.findActivePageSession(bRequireFocus=True)
    dResult = cdpSession.evaluate(sSessionId, submitScript, submitTimeoutSeconds) or {}
    homerLog.info(f"Submit form on {abbreviate(dTarget.get('url', ''), 200)}: {dResult}")
    return dResult
