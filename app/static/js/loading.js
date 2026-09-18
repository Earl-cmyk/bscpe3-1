const skeletonMarkup = (kind = 'line', count = 3) => {
	const item = kind === 'card' ? '<div class="skeleton-card"><span class="skeleton-block short"></span><span class="skeleton-block"></span><span class="skeleton-block medium"></span></div>' : kind === 'calendar' ? '<div class="skeleton-calendar"><span class="skeleton-block"></span><span class="skeleton-block"></span><span class="skeleton-block"></span><span class="skeleton-block"></span><span class="skeleton-block"></span><span class="skeleton-block"></span><span class="skeleton-block"></span></div>' : '<div class="skeleton-line"><span class="skeleton-block short"></span><span class="skeleton-block"></span></div>';
	return Array.from({ length: count }, () => item).join('');
};

function showSkeleton(target, kind = 'line', count = 3) {
	target.innerHTML = skeletonMarkup(kind, count);
	target.setAttribute('aria-busy', 'true');
}

function finishLoading(target) {
	target.removeAttribute('aria-busy');
}
