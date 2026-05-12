# 🌐 S.I.L.O. Target Registry Guide (`registry.py`)

The `registry.py` file acts as the central nervous system for the S.I.L.O. orchestration engine. It tells the Custom Humanizer where to navigate, what DOM elements to interact with, and which network sniffers to activate when analyzing traffic.

By default, S.I.L.O. is configured with **8 Target Domains** and tracks **Google vs. Yahoo** as the primary SSO anchors. 

However, this framework is highly modular. **You can scale the experiment to include as many target websites and custom SSO providers as your local hardware (RAM and CPU) can handle.** ---

## 🛠️ Adding a New Target Website

To add a new platform (e.g., Instagram, LinkedIn, or a niche news site) to the simulation, you only need to update two dictionaries in `registry.py`.

### Step 1: Update the `DOM_MAP`
The Humanizer needs to know the CSS selectors for the site's search bar and feed content to simulate human scrolling, typing, and clicking.

Add your new site to the `DOM_MAP` dictionary using this exact structure:

```python
"Your New Site":  {
    "search_bar": "input[placeholder='Search']", # The CSS selector for the search input
    "feed_text": "article span, div.post-content", # The CSS selectors containing the text the AI will score
    "result_link": "a.post-link" # The CSS selector for clickable posts/results
}