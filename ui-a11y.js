/**
 * UIComponent Accessibility Extension
 * Enhances the base UIComponent with accessibility helpers.
 * This can be merged into ui-components-base.js or kept as a mixin.
 */
class UIAccessibility {
    /**
     * Adds accessibility attributes to an element.
     * @param {HTMLElement} element - Target element
     * @param {Object} attrs - { role, label, description }
     */
    static applyA11y(element, { role, label, description }) {
        if (role) element.setAttribute('role', role);
        if (label) element.setAttribute('aria-label', label);
        if (description) element.setAttribute('aria-describedby', description);
    }
}

// Integrate with UIComponent base
if (window.UIComponent) {
    window.UIComponent.applyA11y = UIAccessibility.applyA11y;
}
