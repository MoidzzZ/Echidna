This is the official implementation of the paper "ECHIDNA: Enhancing Player Engagement via Pre-Explored Branches and Dynamic Role Interaction".

Echidna, Explore branCHes the story dID'nt narrate.

---
We will upload official demo video before 6/8 and offer complete instructions based on the _volcengine_ soon.

To run the code, you should set base_url and api_key in agent/script_writer.py and agent/gama_manager.py, while you should set model_pools in rpg_system/convert.ipynb and rpg_system/app.py.  

**Notice**: you could play directly based on the assets/plot_0524.json without generating a new plot tree, see the last step.

First, You could run branch_system/branch.ipynb to generate plotchains, and run rpg_system/convert.ipynb to convert plotchains to a plot tree.

Then, you could run rpg_system/visual_edit/delete.py to visualize and edit the plot tree.

Finally, you could run rpg_system/app.py to run the game, and open index.html to play.

