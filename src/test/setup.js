import "@testing-library/jest-dom/vitest";

if (!window.matchMedia) {
	window.matchMedia = (query) => ({
		matches: false,
		media: query,
		onchange: null,
		addListener: () => {},
		removeListener: () => {},
		addEventListener: () => {},
		removeEventListener: () => {},
		dispatchEvent: () => false,
	});
}

if (!window.ResizeObserver) {
	window.ResizeObserver = class ResizeObserver {
		observe() {}
		unobserve() {}
		disconnect() {}
	};
}

const originalGetComputedStyle = window.getComputedStyle?.bind(window);
if (originalGetComputedStyle) {
	window.getComputedStyle = (element) => originalGetComputedStyle(element);
}