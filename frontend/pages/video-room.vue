<template>
  <main class="page">
    <h1>Video Room</h1>

    <p class="status">
      Status: {{ connectionStatus }}
    </p>

    <section class="videos">
      <div class="video-card">
        <h2>My Camera</h2>
        <video ref="localVideo" autoplay muted playsinline></video>
      </div>

      <div class="video-card">
        <h2>Remote Camera</h2>
        <video ref="remoteVideo" autoplay playsinline></video>
      </div>
    </section>

    <section class="controls">
      <button @click="startCamera">Start Camera</button>
      <button @click="createOffer" :disabled="!peerConnection">Create Offer</button>
      <button @click="createAnswer" :disabled="!peerConnection">Create Answer</button>
      <button @click="setRemoteDescription" :disabled="!remoteDescriptionText">
        Set Remote Description
      </button>
      <button @click="addRemoteIceCandidates" :disabled="!remoteIceText">
        Add Remote ICE
      </button>
      <button class="danger" @click="hangUp">Hang Up</button>
    </section>

    <section class="box">
      <h2>Local Offer / Answer</h2>
      <textarea v-model="localDescriptionText" readonly></textarea>
      <button @click="copyText(localDescriptionText)">Copy Local Description</button>
    </section>

    <section class="box">
      <h2>Remote Offer / Answer</h2>
      <textarea
        v-model="remoteDescriptionText"
        placeholder="Paste remote offer or answer here"
      ></textarea>
    </section>

    <section class="box">
      <h2>Local ICE Candidates</h2>
      <textarea v-model="localIceText" readonly></textarea>
      <button @click="copyText(localIceText)">Copy Local ICE</button>
    </section>

    <section class="box">
      <h2>Remote ICE Candidates</h2>
      <textarea
        v-model="remoteIceText"
        placeholder="Paste remote ICE candidates here"
      ></textarea>
    </section>
  </main>
</template>

<script setup>
import { ref, onBeforeUnmount } from "vue"

const localVideo = ref(null)
const remoteVideo = ref(null)

const connectionStatus = ref("Not connected")

const localDescriptionText = ref("")
const remoteDescriptionText = ref("")
const localIceText = ref("")
const remoteIceText = ref("")

let localStream = null
let peerConnection = null

const rtcConfig = {
  iceServers: [
    {
      urls: "stun:stun.l.google.com:19302",
    },
  ],
}

async function startCamera() {
  try {
    localStream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    })

    localVideo.value.srcObject = localStream

    createPeerConnection()
    connectionStatus.value = "Camera started"
  } catch (error) {
    console.error(error)
    connectionStatus.value = "Camera error"
  }
}

function createPeerConnection() {
  peerConnection = new RTCPeerConnection(rtcConfig)

  localStream.getTracks().forEach((track) => {
    peerConnection.addTrack(track, localStream)
  })

  peerConnection.ontrack = (event) => {
    remoteVideo.value.srcObject = event.streams[0]
  }

  peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
      localIceText.value += JSON.stringify(event.candidate) + "\n"
    }
  }

  peerConnection.onconnectionstatechange = () => {
    connectionStatus.value = peerConnection.connectionState
  }
}

async function createOffer() {
  const offer = await peerConnection.createOffer()
  await peerConnection.setLocalDescription(offer)

  localDescriptionText.value = JSON.stringify(offer)
}

async function createAnswer() {
  await setRemoteDescription()

  const answer = await peerConnection.createAnswer()
  await peerConnection.setLocalDescription(answer)

  localDescriptionText.value = JSON.stringify(answer)
}

async function setRemoteDescription() {
  if (!remoteDescriptionText.value.trim()) return

  const description = JSON.parse(remoteDescriptionText.value)

  await peerConnection.setRemoteDescription(
    new RTCSessionDescription(description)
  )
}

async function addRemoteIceCandidates() {
  if (!remoteIceText.value.trim()) return

  const candidates = remoteIceText.value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)

  for (const candidateText of candidates) {
    const candidate = JSON.parse(candidateText)

    await peerConnection.addIceCandidate(
      new RTCIceCandidate(candidate)
    )
  }
}

async function copyText(text) {
  await navigator.clipboard.writeText(text)
}

function hangUp() {
  if (peerConnection) {
    peerConnection.close()
    peerConnection = null
  }

  if (localStream) {
    localStream.getTracks().forEach((track) => track.stop())
    localStream = null
  }

  if (localVideo.value) {
    localVideo.value.srcObject = null
  }

  if (remoteVideo.value) {
    remoteVideo.value.srcObject = null
  }

  localDescriptionText.value = ""
  remoteDescriptionText.value = ""
  localIceText.value = ""
  remoteIceText.value = ""
  connectionStatus.value = "Disconnected"
}

onBeforeUnmount(() => {
  hangUp()
})
</script>

<style scoped>
.page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
  font-family: Arial, sans-serif;
}

.status {
  margin-bottom: 20px;
  font-weight: bold;
}

.videos {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.video-card {
  flex: 1;
  min-width: 300px;
}

video {
  width: 100%;
  height: 260px;
  background: #111;
  border-radius: 12px;
}

.controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

button {
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.danger {
  background: #cc3333;
  color: white;
}

.box {
  margin-top: 24px;
}

textarea {
  width: 100%;
  height: 130px;
  padding: 10px;
  border-radius: 8px;
  box-sizing: border-box;
  font-family: monospace;
}
</style>

1. ブラウザAで Start Camera
2. ブラウザBで Start Camera
3. Aで Create Offer
4. Aの Local Offer をコピー
5. Bの Remote Offer / Answer に貼る
6. Bで Create Answer
7. Bの Local Answer をコピー
8. Aの Remote Offer / Answer に貼る
9. Aで Set Remote Description
10. ICE Candidates も相互にコピペして Add Remote ICE
