# Hackathon: “The AGI Assistant”

## 🎯 Overview

Build a **desktop-based AI assistant MVP** that learns how users work by *watching* their screen, *listening* to commands, and then *automating* those same tasks all **locally** on the user’s system.

This challenge reimagines what it means for AI to understand human computer interaction.

Think of it as building your own **AGI assistant** one that watches, learns, and acts.

> The AI observes your desktop → understands what you do → then performs those same actions automatically.
> 

---

## 💡 Objective

Deliver a working prototype that can:

1. **Observe** user actions (record screen + audio).
2. **Understand** what’s happening with that user basically General Personalized LLM (convert to structured JSON + text). **Recognizing** repeated workflows or patterns.
3. **Automate** those same steps through a **Computer Use Platform**.

No login systems, accounts, or servers needed everything should run *locally* and respect privacy.

Your goal: Build the above Pipeline

---

## ⚙️ Core MVP Flow

### 1. Screen & Audio Capture

Your system should act like a **dashcam for the desktop** continuously recording short video clips and screenshots.

Audio can capture commands like “open Excel” or “save report.”

### 2. Data Processing

The system converts:

- Video into **JSON and Screenshots** (to describe actions, clicks, and UI events).
- Audio into **text** (for natural-language understanding).

Everything happens **locally** in user system no cloud uploads.

### 3. Understanding & Pattern Recognition

The AI interprets these files to understand what the user did through personlized text based LLM (or any AI Modal).

For example:

> “User opened Excel, entered a formula in column C, and saved the file.”
> 

Over time, it identifies **repetitive patterns** (e.g., daily report generation). 

Keep on learning with user data.

### 4. Task Automation

Once the workflow is learned, your system should automate it using a **Computer Use Platform**.

This platform should be able to perform day to day user activies that can be:

- Click buttons
- Type into forms
- Navigate between windows
- Perform browser or file operations

### 5. Smart Data Management

Since all processing is local, your system should:

- Delete older training data when a personalized model is stable.
- Optimize how screenshots and videos are stored.
- Manage local storage efficiently.

---

## 🧩 Two-Round Challenge Structure

### ⚡ **Round 1: Observe & Understand (The AGI Assistant)**

> Build the watcher + interpreter — the system that sees, listens, and explains.
> 

### 🎯 Objective

Develop a **desktop application** that:

1. **Captures screen and audio** in real time (like a dashcam).
2. **Transcribes audio** (speech-to-text locally).
3. **Generates structured insights** (text + JSON) describing what’s happening on screen an personalized LLM.
4. **Summarizes or lays down potential automatable workflows** based on observed actions.

### 💡 Expected Outcome

By the end of Round 1, participants should deliver:

- A **working desktop app** (can be .exe, Python, Rust, or Electron-based) that:
    - Records screen & mic input locally.
    - Converts screen activity to descriptive text (even using screenshots + OCR).
    - Transcribes audio locally (using e.g., Whisper.cpp, Vosk, or OpenAI Whisper offline).
    - **Structured JSON** describing UI events, mouse movements, cliks or workflow steps an personalized text based LLM that will understand that user behaviour.
    - **Suggests possible automations** in plain text like:
        
        > “Detected repetitive action: Opening Excel → Typing values → Saving file. Can be automated.”
        > 

### 🧠 Bonus Points

- Using a **lightweight local LLM** (Mistral, Phi-3, or LLaMA.cpp) for understanding actions.
- **Efficient local storage management** (auto-delete older clips).
- **Privacy-first design** (no cloud calls).

### 🧪 Deliverables

- Executable + short demo video (show screen/audio capture + generated workflow text).
- Optional README explaining architecture and LLM flow.

---

### 🚀 **Round 2: Act & Automate (The Computer Use Platform)**

> Build the doer layer — the system that takes over and executes the learned workflows.
> 

### 🎯 Objective

Extend your Round 1 system into a **full “Observe → Understand → Act” AI agent**:

1. **Load learned workflows** from JSON or text descriptions.
2. **Use a Computer Use framework** to execute those steps:
    - Clicks, typing, navigation, etc.
3. **Loop**: Observe → Automate → Verify → Adjust.

### 💡 Expected Outcome

- The assistant can **perform at least one full repetitive task automatically**, e.g.:
    - Open Excel → Fill cells → Save report.
    - Rename downloaded files → Move them to folders.
    - Fill a browser form based on prior runs.

### 🧱 Recommended Tools

- **Stagehand**, **Agent-S**, **Playwright**, **PyAutoGUI**, or **Automa**.
- Integrate with the **Round 1 LLM output** as the “instruction plan.”
- Optionally, create your own small **automation DSL** (e.g., YAML workflow file).

### 🧠 Bonus Points

- Visual dashboard showing detected workflows + toggle to automate.
- Real-time feedback or explainable reasoning ("I'm opening Excel now because…").
- Continual learning: system refines automation as it watches more sessions.

### 🧪 Deliverables

- Executable demo (.exe or local app) showing AI automating at least one learned workflow.
- Short video (3–5 min) demonstrating “learned from Round 1 → executed in Round 2.”

---

## 🧠 Example Use Cases

Participants can decide **any** real-world use case the more creative, the better!

Here are a few ideas:

- Automate repetitive Excel or Google Sheet tasks.
- Fill out forms automatically from past behavior.
- Perform quick browser searches and summarize results.
- Open, rename, and organize files intelligently.

Your flexibility and creativity here will make your project stand out.

---

- 🔗 What is Computer Use?
    
    A **Computer Use Platform** allows an AI to **see your screen, move your cursor, click, type, and interact** — just like a human.
    
    It connects the *reasoning ability* of an LLM with the *action layer* of real computer control.
    
    ### How It Works
    
    1. The AI interprets what needs to be done (e.g., “Search Google for dashcams”).
    2. The Computer Use layer takes over:
        - Opens Chrome
        - Types the query
        - Reads results
        - Copies data
    3. The LLM (via an orchestration layer like **Stagehand**) decides the next step and continues.
    
    This cycle — **Think → Act → Observe → Learn** — forms the backbone of your project.
    
    ### Example Platforms You Can Explore
    
    - **Simular Cloud** — browser-based computer-use sandbox ([simular.ai](https://www.simular.ai/))
    - **Agent S2** — open-source framework for custom agents ([GitHub](https://github.com/simular-ai/Agent-S))
    - **Google Gemini 2.5** — browser control API
    - **Microsoft Copilot Studio** — Windows automation
    - **Hugging Face SmolAgents** — web automation experiments
    
    Your task: **research which platform fits best**, or **build your own lightweight version** if you dare.
    

---

## 🧱 Tech Stack & Reference

You’re free to use any tools, languages, or frameworks.

We’ve already provided a **starter repository** with initial backend work in **Rust** including parts of screen/audio processing and speech-to-text.

👉 REPO LINK FOR REFERENCE: 

https://github.com/HumanityFounders/The-AGI-Assistant

You can:

- **Use this repo as a base but it might be in another tech stack** or either
- **Build it from scratch** fully flexible what works best for you.

---

## 📦 Deliverables

1. **Working MVP (.exe or local build)** — runs fully offline.
2. **Demo Video (3–5 min)** — show the live demo where AI observing, understanding, and automating.

---

## 🏁 Evaluation Criteria

There’s only one rule: **best submission wins.**

---

## 🏆 Prizes & Opportunities

- 🥇 **1st Place:** $(Amazon Voucher/Cash Prize +  Chance to work Experts + Full Time Job Offer + Certificate for 1st Position)
- 🥈 **2nd Place:** $(Claude Code Premium Credits +  Chance to talk with Experts + Might get Job Offer + Certificate for 2nd Position)
- 🥉 **3rd Place:** $(Open AI Premium Credits + Chance to talk with Experts + Certificate for 3rd Position)
- Those who stay till the end and give it their best shot but ultimately don’t end up winning, we’ll be giving a them a Certificate of Appreciation for their hard work, consistency, determination, and dedication.

🏅 The top performers will receive:

- A **Certificate of Excellence**
- An **invitation to join the core team** as a **founding member** with a **high CTC**

---

## 🌟 Closing Note

This hackathon is more than a challenge it’s a chance to **shape your future** while working on one of the most **advanced projects** out there.

It’s a test for your **dedication and obsession** towards your role not just how much you know, but how much you’re willing to figure out.

Build something that *feels alive.*

Something that *watches, learns, and acts.*

Something that says:

> “I understand how you work — let me do it for you.”
> 

It’s a **test of skills over resumes** in the era of AI, you’re **completely free to use any AI tool** to do this assignment. What matters is how smartly you use it and how much ownership you show.

We want to work with **people who enjoy challenges**, the ones who keep pushing even when things break, and **don’t stop until it finally works.**

Once you’re onboard, you’ll be working with a **team of geniuses** people who’ve worked at **NASA** and on some seriously exciting stuff. But before that, you’ve got to **prove you’re the right fit** for this role.

So yeah — thank you for being here, and all the very best for this Hackathon!!

We’re looking forward to connecting/working with the person who can ultimately get recognized as an winner of this challenge.
Also, to those who stay till the end and give it their best shot but ultimately don’t end up winning, we’ll be giving a **Certificate of Appreciation** for their **hard work, consistency, determination, and dedication. Cheers and ALL THE BEST!!!** 😉🔥