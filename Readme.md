This is the official implementation of the paper "ECHIDNA: Enhancing Player Engagement via Pre-Explored Branches and Dynamic Role Interaction".

Echidna, Explore branCHes the story dID'nt NArrate.

---
Our demo can be found in ./demo.

To run the code, you should edit extra/config.py, we use deepseek api based on volcengine.  

**Notice**: you could play directly based on the assets/plot_0524.json without generating a new plot tree, see the last step.

First, You could run branch_system/branch.ipynb to generate plot-chains.

Then, you could run rpg_system/convert.ipynb to convert plotchains to a plot tree, and run rpg_system/visual_edit/delete.py to visualize and edit the plot tree.

Finally, you could run rpg_system/app.py to start, and open index.html to play.

