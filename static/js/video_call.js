document.getElementById("startCamera").addEventListener("click", async () => {
  const localVideo = document.getElementById("localVideo");

  const stream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: true,
  });

  localVideo.srcObject = stream;
});