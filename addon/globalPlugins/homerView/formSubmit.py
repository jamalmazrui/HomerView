"""Submit the form the user is filling in, from whatever field they are in.

requestSubmit rather than submit, and this is the whole point of the module.
form.submit bypasses the form's own validation and never fires its submit
event, so a page that checks its fields in script would never see the attempt
and a required field left empty would be sent anyway. form.requestSubmit does
what pressing the submit button does: it validates, it fires the event, and it
refuses an incomplete form while showing the same message the user would have
seen. An error about a missing field is the correct outcome, not a failure.

A submitter is passed when one can be found, because a form can have several
submit buttons that mean different things, and the browser reports which one
was used. Sending nothing would silently pick the first.
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
    const elForm = el.form || (el.closest ? el.closest("form") : null);
    if (!elForm) {
        // A form built without a form element is common. Fall back to the
        // nearest button that looks like it submits.
        const elButton = el.closest ? el.closest("[role=form], form, body") : null;
        const elSubmit = elButton ? elButton.querySelector(
            'button[type=submit], input[type=submit], button:not([type]), [role=button][data-submit]') : null;
        if (elSubmit) {
            elSubmit.click();
            return {outcome: "submitted", how: "clicked a submit button outside a form element",
                    label: (elSubmit.innerText || elSubmit.value || "").trim().slice(0, 80)};
        }
        return {outcome: "noForm"};
    }
    const elSubmitter = elForm.querySelector(
        'button[type=submit], input[type=submit], button:not([type])');
    const sLabel = elSubmitter
        ? (elSubmitter.innerText || elSubmitter.value || "").trim().slice(0, 80) : "";
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
    dTarget, sSessionId = cdpSession.findActivePageSession()
    dResult = cdpSession.evaluate(sSessionId, submitScript, submitTimeoutSeconds) or {}
    homerLog.info(f"Submit form on {abbreviate(dTarget.get('url', ''), 200)}: {dResult}")
    return dResult
