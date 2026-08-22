/**
 * UIComponent
 * Base class for all stateless UI components.
 * Ensures consistent rendering interface across the design system.
 */
class UIComponent {
    /**
     * Render the component based on provided props.
     * @param {Object} props - Component properties.
     * @returns {string|HTMLElement} - The rendered HTML string or DOM element.
     */
    render(props) {
        throw new Error('render() must be implemented by subclasses');
    }

    /**
     * Utility to create element with specified classes and attributes.
     */
    createElement(tag, props = {}, children = []) {
        const element = document.createElement(tag);

        if (props.className) element.className = props.className;
        if (props.id) element.id = props.id;

        Object.entries(props).forEach(([key, value]) => {
            if (key !== 'className' && key !== 'id') {
                element.setAttribute(key, value);
            }
        });

        if (Array.isArray(children)) {
            children.forEach(child => {
                if (typeof child === 'string') {
                    element.appendChild(document.createTextNode(child));
                } else if (child instanceof HTMLElement) {
                    element.appendChild(child);
                }
            });
        } else if (children) {
            element.innerHTML = children;
        }

        return element;
    }
}

// Export for use in other components
window.UIComponent = UIComponent;
