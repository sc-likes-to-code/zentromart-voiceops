# ZentroMart VoiceOps — OBS Studio Recording Runbook

This runbook provides step-by-step instructions for recording the final demonstration video for the IIT Guwahati × Gnani.ai VoiceOps Capstone 2026.

Follow these instructions to guarantee crisp 1080p visuals, perfect audio synchronization, and zero audio-dropout issues.

---

## 1. Root Cause of Previous Missing Audio & How to Avoid It

In earlier recordings, terminal text was visible but synthesized Gnani voice audio was missing. Investigation identified two separate causes:
1. **Invalid WAV Headers from Streaming TTS**: Gnani's raw streaming output contained `0xFFFFFFFF` in the RIFF chunk header, causing Windows `winsound` to stop prematurely.
   *Resolution*: The audio pipeline now uses `repair_wav_header()`, which writes exact byte lengths into the RIFF and data chunk headers. All demo audio files now play to full duration.
2. **OBS Audio Source Configuration**: OBS was capturing only the microphone input and had no **"Audio Output Capture"** (Desktop Audio) enabled. As a result, sounds played by Windows apps (`winsound`) were never routed to the video track.
   *Resolution*: You must add **Audio Output Capture** in OBS Studio (see Section 3 below).

---

## 2. Pre-Flight Checklist

Before launching OBS, open PowerShell in `E:\MY PROJECTS\zentromart-voiceops`:

1. **Activate Virtual Environment**:
   ```powershell
   cd "E:\MY PROJECTS\zentromart-voiceops"
   .\.venv\Scripts\activate
   ```

2. **Verify Credentials**:
   Confirm that `.env` contains:
   ```env
   GEMINI_API_KEY=AIzaSy...
   GNANI_API_KEY=gnani_...
   ```

3. **Verify Audio Output with Live Sound Test**:
   Run this command in PowerShell:
   ```powershell
   python -c "import winsound; winsound.PlaySound('outputs/sample_outputs/sample_test_tone.wav', winsound.SND_FILENAME)"
   ```
   *Requirement*: You must hear a clear tone through your speakers/headphones.

4. **Verify Pre-Staged Demonstration Audio Files**:
   Ensure all three demonstration audio files exist:
   - `demo/audio/scenario_a/01_return_window.m4a`
   - `demo/audio/scenario_a/02_pickup_fee.wav`
   - `demo/audio/scenario_b/01_damage_escalation.wav`

---

## 3. OBS Studio Configuration (One-Time Setup)

### A. Video Canvas Settings
1. Open **OBS Studio**.
2. Go to **Settings → Video**:
   - **Base (Canvas) Resolution**: `1920x1080`
   - **Output (Scaled) Resolution**: `1920x1080`
   - **Downscale Filter**: `Bicubic` or `Lanczos`
   - **Common FPS Values**: `30` (or `60`)
3. Click **Apply**.

### B. Audio Mixer Setup (CRITICAL FOR TTS AUDIO)
Under the **Sources** dock (bottom left):

1. **Add Desktop Audio (Agent Voice)**:
   - Click `+` → **Audio Output Capture**.
   - Name it: `Desktop / Speaker Audio`.
   - **Device**: Select `Default` (or the specific speakers/headphones you are listening with).
   - *Verification*: While running the sound test command from Section 2, watch the OBS **Audio Mixer** volume meter. The green/yellow bar for `Desktop / Speaker Audio` **MUST bounce**.

2. **Add Presenter Microphone (Your Narration)**:
   - Click `+` → **Audio Input Capture**.
   - Name it: `Presenter Mic`.
   - **Device**: Select your active microphone.
   - *Verification*: Speak a few words; confirm the `Presenter Mic` meter bounces.

3. **Balance the Levels**:
   - Set `Desktop / Speaker Audio` to approximately `-3.0 dB` to `-5.0 dB`.
   - Set `Presenter Mic` to approximately `-2.0 dB` to `-4.0 dB`.
   - Make sure neither meter hits the red zone (+0.0 dB clipping).

### C. Visual Scene Setup
Under **Sources**:
1. Click `+` → **Window Capture**.
2. Select your PowerShell / Windows Terminal window.
3. In your Terminal settings:
   - Color Scheme: Dark theme (e.g. Campbell, One Half Dark).
   - Font: `Cascadia Code` or `Consolas`, size `18pt` or `20pt` for maximum readability.
   - Window size: Fill the canvas cleanly.

### D. Recording Output Settings
In **Settings → Output → Recording**:
- **Recording Format**: `mp4` (or `mkv` remuxed to `mp4`).
- **Video Encoder**: `NVIDIA NVENC H.264` (if GPU available) or `x264`.
- **Audio Encoder**: `AAC`.
- **Rate Control**: `CBR` (6000–8000 Kbps).

---

## 4. Step-by-Step Recording Procedure

### Dry Run (Rehearsal)
Run the script once before recording to see the exact cadence and ensure local models/APIs are warm:
```powershell
python demo/run_live_demo.py
```
Observe the live playback of Kaveri's voice for each turn.

---

### Official Recording Take

1. **Clear Terminal**:
   ```powershell
   cls
   ```
2. **Hit "Start Recording"** in OBS Studio.
3. **Turn 0 (0:00 – 0:12)**:
   - Speak your introductory voiceover (see [demo_script.md](demo_script.md)):
     > *"Welcome to the live demonstration of ZentroMart VoiceOps..."*
4. **Trigger Live Pipeline**:
   - In terminal, type and press Enter:
     ```powershell
     python demo/run_live_demo.py
     ```
5. **Scenario A (0:12 – 1:00)**:
   - Presenter narrates Turn 1 query.
   - Agent synthesizes Kaveri speech → **Stay quiet and let Kaveri speak**.
   - Presenter narrates Turn 2 follow-up ("it" pronoun context preservation).
   - Agent synthesizes Kaveri speech → **Stay quiet and let Kaveri speak**.
6. **Scenario B (1:00 – 1:35)**:
   - Presenter narrates high-value damage inquiry (> ₹10,000 threshold).
   - Terminal prints decision `ESCALATE` and rule `DWM-3`.
   - Kaveri speaks escalation instructions.
7. **Outro & Benchmark Summary (1:35 – 1:50)**:
   - Highlight the benchmark metrics: 100% decision accuracy, zero prohibited claims, 67 unit tests passing.
   - Conclude demonstration.
8. **Hit "Stop Recording"** in OBS Studio immediately.

---

## 5. Post-Recording Quality Verification

Open the recorded `.mp4` file in VLC or Windows Media Player and verify:
1. **Total Duration**: Must be under 120 seconds (ideal: 100–110s).
2. **Audio Track**:
   - Can you hear your own voiceover clearly?
   - Can you hear Kaveri's synthetic voice clearly during each agent response?
   - Is there any stutter, echo, or premature cutoff?
3. **Video Track**:
   - Is the terminal text crisp, sharp, and easy to read at 1080p?
   - Are the chunk IDs and `ANSWER` / `ESCALATE` decisions clearly visible?

If any audio is missing, check OBS **Audio Mixer → Advanced Audio Properties** to ensure both sources have Track 1 checked.
