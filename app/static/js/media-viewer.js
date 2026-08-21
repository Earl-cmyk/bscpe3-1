const mediaModal = document.querySelector('#mediaModal');
const mediaModalContent = document.querySelector('#mediaModalContent');
const mediaModalName = document.querySelector('#mediaModalName');
const mediaModalDownload = document.querySelector('#mediaModalDownload');

function closeMediaModal() {
  const video = mediaModalContent.querySelector('video');
  if (video) {
    video.pause();
    video.removeAttribute('src');
    video.load();
  }
  mediaModalContent.replaceChildren();
  mediaModal.hidden = true;
}

function openMediaModal(target) {
  const url = target.dataset.mediaUrl;
  const name = target.dataset.mediaName || 'Attachment';
  const type = target.dataset.mediaType || '';
  const media = type.startsWith('video/') ? document.createElement('video') : document.createElement('img');
  media.src = url;
  media.className = 'media-modal-media';
  media.alt = name;
  if (media.tagName === 'VIDEO') {
    media.controls = true;
    media.playsInline = true;
    media.preload = 'metadata';
  }
  mediaModalContent.replaceChildren(media);
  mediaModalName.textContent = name;
  mediaModalDownload.href = `${url}${url.includes('?') ? '&' : '?'}download=1`;
  mediaModal.hidden = false;
  mediaModal.querySelector('.close').focus();
}

document.addEventListener('click', (event) => {
  const target = event.target.closest('[data-media-url]');
  if (target) {
    event.preventDefault();
    openMediaModal(target);
    return;
  }
  if (event.target === mediaModal || event.target.closest('[data-close="mediaModal"]')) closeMediaModal();
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !mediaModal.hidden) closeMediaModal();
});