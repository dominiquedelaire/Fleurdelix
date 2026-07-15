**Titre :** Créer son propre modèle local à partir d’un modèle existant performant   
**Date de création :** 14 Juillet 2026   
**Auteur :** Dominique Delaire

<p><strong>L'objectif de ce tutoriel est de vous montrer comment créer son propre modèle IA à partir d'un autre et l'embellir avec notre contexte, nos données, etc... et le publier. Tout cela avec des outils open source ou gratuits :)</strong></p>
<p><strong>Nous allons bâtir un modèle en lien avec le management et des conseils sur la gestion des ressources.</strong></p>
<p><strong>Ceci est un modèle exemple, celui qui est disponible dans notre boutique est beaucoup plus précis et a énormément de contenus en management pour les décideurs, Vp, Directeurs, etc...</strong></p>
<h3><strong>Prérequis</strong></h3>
<p>Tous les prérequis sont déjà installés dans Fleurdelix (Anciennement ShellbotsOS). Voici les informations pour les autres systèmes d'exploitation :</p>
<ul>
<li>Avoir au moins une carte Nvidia RTX 3060<br>
</li>
<li>les drivers nvidia à jour sous Fleurdelix ou linux Ubuntu</li>
<li>CUDA : une plateforme de calcul parallèle développée par Nvidia (Bibliothèques, outils et langages). Pour les développeurs et qui permet d'utiliser la puissance de calcul des gpu nvidia.</li>
<li>Python3, Pytorch avec support Cuda</li>
<li>Qlora, librairies Hugging Face (modèle Phi-3 et dataset sur le management)</li>
<li>Ollama<br>
</li>
</ul>
<h3><strong>Validation des prérequis</strong></h3>
<ul>
<li>Vérification Nvidia et drivers :
<ul>
<li>Tapez la commande dans un terminal <strong>nvidia-smi</strong>
</li>
<li>
<strong></strong><strong></strong>Cela vous permet de voir si vous avez une carte nvidia, quelle version, la version de CUDA aussi (<strong>noter la version, cela va nous servir plus tard</strong><img width="1074" height="792" alt="img1" src="https://github.com/user-attachments/assets/52c71537-ed19-4f4c-9069-2b6f18d277c0" />
<strong></strong>
</li>
</ul>
</li>
<li>Pour mettre à jour vos drivers nvidia si c'est requis : 
<ul>
<li>taper :
<ul>
<li style="font-weight: bold;"><strong>sudo apt update</strong></li>
<li style="font-weight: bold;"><strong>sudo apt upgrade -y</strong></li>
<li style="font-weight: bold;"><strong>sudo apt autoremove -y</strong></li>
<li>puis pour mettre à jour vos drivers : <strong>sudo ubuntu-drivers autoinstall</strong>
</li>
<li>le système vous demandera de rebooter :<strong> sudo reboot</strong>
</li>
</ul>
</li>
</ul>
</li>
<li>
<strong></strong>Vérifier si Python 3.10 minimum est installé. ShellbotsOS vient avec Python préinstallé.</li>
<li>Pour installer Python 3.10 : <strong>sudo apt install python3-pip python3-venv -y</strong>
</li>
<li>Nous allons maintenant créer un répertoire spécifique et un environnement virtuel pour notre projet <strong>:</strong>
<ul>
<li><strong>mkdir ~/finetune_modelshellbotsnano<br>cd ~/finetune_modelshellbotsnano<br>python3 -m venv finetune_env</strong></li>
</ul>
</li>
<li>Activation de l'environnement virtuel :
<ul>
<li><strong>source finetune_env/bin/activate</strong></li>
</ul>
</li>
<li>le fait d'avoir (finetune_env) devant le prompt indique que l'environnement virtuel est actif<strong></strong><strong></strong>
</li>
<li><strong>  <img width="1214" height="720" alt="img2" src="https://github.com/user-attachments/assets/503b2b74-e6bd-4bd1-a1ca-b15dcbd19117" />
</strong></li>
<li>
<strong></strong>Maintenant il est nécessaire si ce n'est pas déjà fait, d'installer le framework ML principal, Pytorch, mais qui correspond à notre version de Cuda. Dans notre premier écran, la version indiquait 12.8, donc la commande pour installer pytorch est :
<ul>
<li style="font-weight: bold;"><strong>pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128</strong></li>
</ul>
</li>
<li>Ensuite, nous allons installer les bibliothèques nécessaires pour Qlora et Hugging face (j'y reviendrais en détail tout à l'heure) pour fine tune le modèle :
<ul>
<li style="font-weight: bold;"><strong>pip install transformers peft bitsandbytes accelerate datasets trl scipy</strong></li>
</ul>
</li>
<li>Ensuite, si ce n'est déjà pas fait dans votre environnement, nous allons installer Ollama (de meta), l'outil permettant d'exécuter notre modèle finetuné localement : 
<ul>
<li style="font-weight: bold;"><strong>curl -fsSL https://ollama.com/install.sh | sh</strong></li>
<li>Vous pouvez vérifier ensuite l'installation par :
<ul>
<li style="font-weight: bold;"><strong>ollama --version</strong></li>
</ul>
</li>
<li>Et tester un petit modèle et vérifiez si le GPU est bien utilisé (nvidia-msi) pendant que vous lancez la commande <strong>ollama run llama2:7b </strong>et téléchargez le modèle et posez des questions :) 
<ul>
<li>  <img width="1161" height="672" alt="img3" src="https://github.com/user-attachments/assets/da27f976-1911-40ab-bcc7-244f1f911ad8" />
</li>
</ul>
</li>
</ul>
</li>
<li>Nous avons maintenant tous les éléments et prérequis pour commencer à "finetuner" un modèle existant.</li>
</ul>
<h3><strong> Préparation des données d'entraînement</strong></h3>
<p>Pour notre tutoriel, nous utilisons le modèle <b>Phi-3 Mini</b> de Microsoft. Ce modèle est un excellent exemple de <b>Small Language Model (SLM)</b> : il est <b>performant</b> malgré sa petite taille (3.8 milliards de paramètres). Nous allons y ajouter des données sur le management et la gestion des ressources avec un dataset assez connu sur hugging face : <a href="https://huggingface.co/datasets/tatsu-lab/alpaca/viewer/default/train?q=management" title="https://huggingface.co/datasets/tatsu-lab/alpaca/viewer/default/train?q=management" rel="noopener" target="_blank">https://huggingface.co/datasets/tatsu-lab/alpaca/viewer/default/train?q=management</a></p>
<p>C'est pour cette raison qu'il est idéal pour l'IA locale : il offre un équilibre parfait entre des résultats de haute qualité et la possibilité de s'exécuter sur des GPU NVIDIA grand public.</p>
<p>Le <b>fine-tuning</b> de modèles comme celui-ci est rendu possible grâce à l'écosystème <b>Hugging Face</b>, qui sert de <b>"GitHub de l'IA"</b> : c'est le dépôt central où le modèle de base (<code>microsoft/Phi-3-mini-4k-instruct</code>) est hébergé via leur bibliothèque <b><code>transformers</code></b>.</p>
<p>Afin d'adapter ce modèle sur votre GPU NVIDIA sans surcharger la VRAM, nous utilisons la technique <b>LoRA</b> (<i>Low-Rank Adaptation</i>). Au lieu de réentraîner les milliards de paramètres du modèle (ce qui est impossible en local), LoRA ajoute et ajuste seulement de <b>petites matrices d'adaptation</b> (les "adaptateurs") qui apprennent la nouvelle spécialisation.</p>
<p>Nous utilisons spécifiquement <b>QLoRA</b> (<i>Quantized LoRA</i>), la version la plus efficace en ressources. QLoRA utilise des outils de <b>quantification 4-bit</b> (<code>bitsandbytes</code>) pour réduire la taille du modèle de base au maximum, lui permettant de <b>tenir dans votre VRAM</b> pendant que LoRA se charge de l'apprentissage ciblé.</p>
<p>En utilisant les bibliothèques <b><code>peft</code></b> et <b><code>trl</code></b> de Hugging Face, on orchestre l'ensemble de ce processus de manière optimisée.</p>
<p> </p>
<p>Voici le code python permettant de formater nos données du dataset et enseigner au modèle de base Phi-3Mini) : </p>
<p>Explications du code :</p>
<ul>
<li>Configuration et chargement des librairies</li>
<li>Préparation des données et Tokenization</li>
<li>Configuration de la quantification (Qlora)</li>
<li>Chargement du modèle et Configuration Lora</li>
<li>Configuration de l'entraîneur (SFTTrainer)</li>
<li>Lancement de l'entraînement et sauvegarde</li>
</ul>

# Début du code
<div style="color: #cccccc; background-color: #1f1f1f; font-family: 'Droid Sans Mono', 'monospace', monospace; font-weight: normal; font-size: 8px; line-height: 6px; white-space: pre;">
<div><span style="color: #6a9955;"># Tutoriel finetuning de modèles</span></div>
<div><span style="color: #6a9955;"># Dominique Delaire</span></div>
<div><span style="color: #6a9955;"></span></div>
<br>
<div>
<span style="color: #c586c0;">import</span><span style="color: #cccccc;"> </span><span style="color: #4ec9b0;">torch</span>
</div>
<div>
<span style="color: #c586c0;">import</span><span style="color: #cccccc;"> </span><span style="color: #4ec9b0;">os</span>
</div>
<div>
<span style="color: #c586c0;">import</span><span style="color: #cccccc;"> </span><span style="color: #4ec9b0;">warnings</span>
</div>
<div>
<span style="color: #c586c0;">import</span><span style="color: #cccccc;"> </span><span style="color: #4ec9b0;">logging</span><span style="color: #cccccc;"> </span>
</div>
<div>
<span style="color: #c586c0;">from</span><span style="color: #cccccc;"> datasets </span><span style="color: #c586c0;">import</span><span style="color: #cccccc;"> load_dataset</span>
</div>
<div><span style="color: #6a9955;"># CORRECTION D'IMPORTATION : LoraConfig et PeftModel viennent de peft</span></div>
<div>
<span style="color: #c586c0;">from</span><span style="color: #cccccc;"> peft </span><span style="color: #c586c0;">import</span><span style="color: #cccccc;"> LoraConfig, PeftModel </span>
</div>
<div><span style="color: #6a9955;"># CORRECTION D'IMPORTATION : BitsAndBytesConfig et autres viennent de transformers</span></div>
<div>
<span style="color: #c586c0;">from</span><span style="color: #cccccc;"> transformers </span><span style="color: #c586c0;">import</span><span style="color: #cccccc;"> AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments </span>
</div>
<div>
<span style="color: #c586c0;">from</span><span style="color: #cccccc;"> trl </span><span style="color: #c586c0;">import</span><span style="color: #cccccc;"> SFTTrainer</span>
</div>
<br>
<div><span style="color: #6a9955;"># filtre des logs</span></div>
<div><span style="color: #6a9955;"># Masquer l'avertissement de trl sur 'tokenizer'</span></div>
<div>
<span style="color: #4ec9b0;">warnings</span><span style="color: #cccccc;">.</span><span style="color: #dcdcaa;">filterwarnings</span><span style="color: #cccccc;">(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #ce9178;">"ignore"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">message</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"`tokenizer` is deprecated and will be removed in version 5.0.0 for `SFTTrainer.__init__`.*"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">category</span><span style="color: #d4d4d4;">=</span><span style="color: #4ec9b0;">FutureWarning</span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<div><span style="color: #6a9955;"># Cacher les warnings des librairies (casting torch, etc.)</span></div>
<div>
<span style="color: #4ec9b0;">logging</span><span style="color: #cccccc;">.</span><span style="color: #dcdcaa;">getLogger</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"transformers"</span><span style="color: #cccccc;">).</span><span style="color: #dcdcaa;">setLevel</span><span style="color: #cccccc;">(</span><span style="color: #4ec9b0;">logging</span><span style="color: #cccccc;">.</span><span style="color: #9cdcfe;">ERROR</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #4ec9b0;">logging</span><span style="color: #cccccc;">.</span><span style="color: #dcdcaa;">getLogger</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"trl"</span><span style="color: #cccccc;">).</span><span style="color: #dcdcaa;">setLevel</span><span style="color: #cccccc;">(</span><span style="color: #4ec9b0;">logging</span><span style="color: #cccccc;">.</span><span style="color: #9cdcfe;">ERROR</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #4ec9b0;">warnings</span><span style="color: #cccccc;">.</span><span style="color: #dcdcaa;">filterwarnings</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"ignore"</span><span style="color: #cccccc;">, </span><span style="color: #9cdcfe;">category</span><span style="color: #d4d4d4;">=</span><span style="color: #4ec9b0;">UserWarning</span><span style="color: #cccccc;">)</span>
</div>
<br><br>
<div><span style="color: #6a9955;"># variables de config</span></div>
<br>
<div>
<span style="color: #4fc1ff;">MODEL_NAME</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"microsoft/Phi-3-mini-4k-instruct"</span>
</div>
<div>
<span style="color: #4fc1ff;">DATASET_NAME</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"tatsu-lab/alpaca"</span><span style="color: #cccccc;"> </span>
</div>
<div>
<span style="color: #4fc1ff;">OUTPUT_DIR</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"./phi3_management_checkpoint"</span><span style="color: #cccccc;"> </span>
</div>
<div>
<span style="color: #4fc1ff;">MERGED_MODEL_PATH</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"./shellbots_model"</span><span style="color: #cccccc;"> </span>
</div>
<div>
<span style="color: #4fc1ff;">MANAGEMENT_KEYWORDS</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> [</span><span style="color: #ce9178;">"team"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"manager"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"leadership"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"business strategy"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"project plan"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"employee"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"meeting"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"productivity"</span><span style="color: #cccccc;">]</span>
</div>
<br>
<div>
<span style="color: #c586c0;">if</span><span style="color: #cccccc;"> </span><span style="color: #569cd6;">not</span><span style="color: #cccccc;"> </span><span style="color: #4ec9b0;">torch</span><span style="color: #cccccc;">.cuda.is_available():</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #c586c0;">raise</span><span style="color: #cccccc;"> </span><span style="color: #4ec9b0;">SystemError</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"CUDA n'est pas disponible."</span><span style="color: #cccccc;">)</span>
</div>
<br>
<div><span style="color: #6a9955;"># On doit formater les données comme un prompt avec des réponses</span></div>
<br>
<div>
<span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> AutoTokenizer.from_pretrained(</span><span style="color: #4fc1ff;">MODEL_NAME</span><span style="color: #cccccc;">, </span><span style="color: #9cdcfe;">trust_remote_code</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;">.pad_token </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;">.eos_token </span>
</div>
<br>
<div>
<span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;">.padding_side </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">'right'</span><span style="color: #cccccc;"> </span>
</div>
<br>
<div>
<span style="color: #569cd6;">def</span><span style="color: #cccccc;"> </span><span style="color: #dcdcaa;">format_data</span><span style="color: #cccccc;">(</span><span style="color: #9cdcfe;">example</span><span style="color: #cccccc;">):</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #c586c0;">return</span><span style="color: #cccccc;"> {</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #ce9178;">"text"</span><span style="color: #cccccc;">: </span><span style="color: #569cd6;">f</span><span style="color: #ce9178;">"### Instruction: </span><span style="color: #569cd6;">{</span><span style="color: #9cdcfe;">example</span><span style="color: #cccccc;">[</span><span style="color: #ce9178;">'instruction'</span><span style="color: #cccccc;">]</span><span style="color: #569cd6;">}</span><span style="color: #d7ba7d;">\n</span><span style="color: #ce9178;">### Réponse: </span><span style="color: #569cd6;">{</span><span style="color: #9cdcfe;">example</span><span style="color: #cccccc;">[</span><span style="color: #ce9178;">'output'</span><span style="color: #cccccc;">]</span><span style="color: #569cd6;">}{</span><span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;">.eos_token</span><span style="color: #569cd6;">}</span><span style="color: #ce9178;">"</span>
</div>
<div><span style="color: #cccccc;"> }</span></div>
<br>
<div><span style="color: #6a9955;"># QLoRA et modèle avec flash_attention pour les performances</span></div>
<br>
<div>
<span style="color: #9cdcfe;">bnb_config</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> BitsAndBytesConfig(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">load_in_4bit</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bnb_4bit_quant_type</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"nf4"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bnb_4bit_compute_dtype</span><span style="color: #d4d4d4;">=</span><span style="color: #4ec9b0;">torch</span><span style="color: #cccccc;">.float16, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bnb_4bit_use_double_quant</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">False</span><span style="color: #cccccc;">,</span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<br>
<div>
<span style="color: #9cdcfe;">lora_config</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> LoraConfig(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">r</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">16</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">lora_alpha</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">32</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">lora_dropout</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">0.05</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">target_modules</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"all-linear"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bias</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"none"</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">task_type</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"CAUSAL_LM"</span><span style="color: #cccccc;">, </span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<br>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #569cd6;">f</span><span style="color: #ce9178;">"Chargement du modèle </span><span style="color: #569cd6;">{</span><span style="color: #4fc1ff;">MODEL_NAME</span><span style="color: #569cd6;">}</span><span style="color: #ce9178;"> en QLoRA avec Flash Attention 2..."</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">model</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> AutoModelForCausalLM.from_pretrained(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #4fc1ff;">MODEL_NAME</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">quantization_config</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">bnb_config</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">dtype</span><span style="color: #d4d4d4;">=</span><span style="color: #4ec9b0;">torch</span><span style="color: #cccccc;">.float16, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">device_map</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"auto"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">trust_remote_code</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">attn_implementation</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"flash_attention_2"</span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<div>
<span style="color: #9cdcfe;">model</span><span style="color: #cccccc;">.config.use_cache </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #569cd6;">False</span><span style="color: #cccccc;"> </span>
</div>
<div>
<span style="color: #9cdcfe;">model</span><span style="color: #cccccc;">.config.pretraining_tp </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #b5cea8;">1</span><span style="color: #cccccc;"> </span>
</div>
<br>
<div><span style="color: #6a9955;"># on charge le dataset exemple sur le management</span></div>
<br>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #569cd6;">f</span><span style="color: #ce9178;">"Téléchargement et filtrage du dataset </span><span style="color: #569cd6;">{</span><span style="color: #4fc1ff;">DATASET_NAME</span><span style="color: #569cd6;">}</span><span style="color: #ce9178;">..."</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">dataset</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> load_dataset(</span><span style="color: #4fc1ff;">DATASET_NAME</span><span style="color: #cccccc;">, </span><span style="color: #9cdcfe;">split</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"train"</span><span style="color: #cccccc;">) </span>
</div>
<div>
<span style="color: #9cdcfe;">dataset</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">dataset</span><span style="color: #cccccc;">.filter(</span><span style="color: #569cd6;">lambda</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">x</span><span style="color: #cccccc;">: </span><span style="color: #dcdcaa;">any</span><span style="color: #cccccc;">(</span><span style="color: #9cdcfe;">k</span><span style="color: #cccccc;"> </span><span style="color: #c586c0;">in</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">x</span><span style="color: #cccccc;">[</span><span style="color: #ce9178;">'instruction'</span><span style="color: #cccccc;">].lower() </span><span style="color: #c586c0;">for</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">k</span><span style="color: #cccccc;"> </span><span style="color: #c586c0;">in</span><span style="color: #cccccc;"> </span><span style="color: #4fc1ff;">MANAGEMENT_KEYWORDS</span><span style="color: #cccccc;">))</span>
</div>
<div>
<span style="color: #9cdcfe;">dataset</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">dataset</span><span style="color: #cccccc;">.map(</span><span style="color: #dcdcaa;">format_data</span><span style="color: #cccccc;">, </span><span style="color: #9cdcfe;">remove_columns</span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;">[</span><span style="color: #ce9178;">"instruction"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"output"</span><span style="color: #cccccc;">, </span><span style="color: #ce9178;">"input"</span><span style="color: #cccccc;">]) </span>
</div>
<br>
<div><span style="color: #6a9955;"># Entrainement avec les données du dataset</span></div>
<br>
<div>
<span style="color: #9cdcfe;">training_arguments</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> TrainingArguments(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">output_dir</span><span style="color: #d4d4d4;">=</span><span style="color: #4fc1ff;">OUTPUT_DIR</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">num_train_epochs</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">3</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">per_device_train_batch_size</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">2</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">gradient_accumulation_steps</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">2</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">optim</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"paged_adamw_32bit"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">logging_steps</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">50</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">learning_rate</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">2e-4</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">weight_decay</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">0.001</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">fp16</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bf16</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">False</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">max_grad_norm</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">0.3</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">warmup_ratio</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">0.03</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">group_by_length</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">lr_scheduler_type</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"cosine"</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">save_strategy</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"epoch"</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">report_to</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"none"</span><span style="color: #cccccc;">, </span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<br>
<div>
<span style="color: #9cdcfe;">trainer</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> SFTTrainer(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">model</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">model</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">train_dataset</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">dataset</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">peft_config</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">lora_config</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">dataset_text_field</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"text"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">max_seq_length</span><span style="color: #d4d4d4;">=</span><span style="color: #b5cea8;">512</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">tokenizer</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">args</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">training_arguments</span><span style="color: #cccccc;">,</span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<br>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"</span><span style="color: #d7ba7d;">\n</span><span style="color: #ce9178;">Début du Fine-Tuning..."</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">trainer</span><span style="color: #cccccc;">.train()</span>
</div>
<br>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"</span><span style="color: #d7ba7d;">\n</span><span style="color: #ce9178;">Terminé ! Sauvegarde des adaptateurs..."</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">trainer</span><span style="color: #cccccc;">.model.save_pretrained(</span><span style="color: #4fc1ff;">OUTPUT_DIR</span><span style="color: #cccccc;">) </span>
</div>
<br>
<div><span style="color: #6a9955;"># Fusion du modèle</span></div>
<br>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"Fusion du modèle..."</span><span style="color: #cccccc;">)</span>
</div>
<div><span style="color: #6a9955;"># Libérer le GPU</span></div>
<div>
<span style="color: #c586c0;">del</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">model</span><span style="color: #cccccc;">, </span><span style="color: #9cdcfe;">trainer</span><span style="color: #cccccc;"> </span>
</div>
<div>
<span style="color: #4ec9b0;">torch</span><span style="color: #cccccc;">.cuda.empty_cache() </span>
</div>
<br>
<div><span style="color: #6a9955;"># Réutilisation de la config QLORA (critique pour la basse RAM)</span></div>
<div>
<span style="color: #9cdcfe;">bnb_config_merge</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> BitsAndBytesConfig(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">load_in_4bit</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bnb_4bit_quant_type</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"nf4"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bnb_4bit_compute_dtype</span><span style="color: #d4d4d4;">=</span><span style="color: #4ec9b0;">torch</span><span style="color: #cccccc;">.float16, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">bnb_4bit_use_double_quant</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">False</span><span style="color: #cccccc;">,</span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<br>
<div><span style="color: #6a9955;"># Rechargement du modèle de base </span></div>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"Chargement du modèle de base pour la fusion..."</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">base_model</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> AutoModelForCausalLM.from_pretrained(</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #4fc1ff;">MODEL_NAME</span><span style="color: #cccccc;">,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">quantization_config</span><span style="color: #d4d4d4;">=</span><span style="color: #9cdcfe;">bnb_config_merge</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">dtype</span><span style="color: #d4d4d4;">=</span><span style="color: #4ec9b0;">torch</span><span style="color: #cccccc;">.float16,</span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">device_map</span><span style="color: #d4d4d4;">=</span><span style="color: #ce9178;">"auto"</span><span style="color: #cccccc;">, </span>
</div>
<div>
<span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">trust_remote_code</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span>
</div>
<div><span style="color: #cccccc;">)</span></div>
<br>
<div><span style="color: #6a9955;"># Fusion des adaptateurs sur le modèle </span></div>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #ce9178;">"Fusion des adaptateurs PEFT..."</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">merged_model</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> PeftModel.from_pretrained(</span><span style="color: #9cdcfe;">base_model</span><span style="color: #cccccc;">, </span><span style="color: #4fc1ff;">OUTPUT_DIR</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">merged_model</span><span style="color: #cccccc;"> </span><span style="color: #d4d4d4;">=</span><span style="color: #cccccc;"> </span><span style="color: #9cdcfe;">merged_model</span><span style="color: #cccccc;">.merge_and_unload() </span>
</div>
<br>
<div><span style="color: #6a9955;"># On sauvegarde le modèle</span></div>
<div>
<span style="color: #4ec9b0;">os</span><span style="color: #cccccc;">.</span><span style="color: #dcdcaa;">makedirs</span><span style="color: #cccccc;">(</span><span style="color: #4fc1ff;">MERGED_MODEL_PATH</span><span style="color: #cccccc;">, </span><span style="color: #9cdcfe;">exist_ok</span><span style="color: #d4d4d4;">=</span><span style="color: #569cd6;">True</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">merged_model</span><span style="color: #cccccc;">.save_pretrained(</span><span style="color: #4fc1ff;">MERGED_MODEL_PATH</span><span style="color: #cccccc;">)</span>
</div>
<div>
<span style="color: #9cdcfe;">tokenizer</span><span style="color: #cccccc;">.save_pretrained(</span><span style="color: #4fc1ff;">MERGED_MODEL_PATH</span><span style="color: #cccccc;">)</span>
</div>
<br>
<div>
<span style="color: #dcdcaa;">print</span><span style="color: #cccccc;">(</span><span style="color: #569cd6;">f</span><span style="color: #ce9178;">"Modèle fusionné prêt dans : </span><span style="color: #569cd6;">{</span><span style="color: #4fc1ff;">MERGED_MODEL_PATH</span><span style="color: #569cd6;">}</span><span style="color: #ce9178;">"</span><span style="color: #cccccc;">)</span>
</div>
</div>
<p> </p>

<p>Voici ce que cela donne à l'exécution pour créer et fusionné notre modèle Phi-3 avec nos données du dataset :</p>
<p>  <img width="1242" height="839" alt="img4" src="https://github.com/user-attachments/assets/91d083cf-4955-4f55-a7e3-0eee005f2363" />
</p>
<h3><strong>Posts Traitements de notre modèle</strong></h3>
<p>Une fois le modèle entraîné et sauvegardé, si on veut l'exploiter avec <strong>Ollama</strong>, il est nécessaire <strong>de convertir notre modèle au format GGUF</strong>. </p>
<p>Le <strong>GGUF</strong> (Gpt-GEneration Unified Format), est un format de fichier binaire spécialement conçu pour l'inférence des modèles de langages (LLM) sur le CPU et le GPU. C'est le format standard utilisé par plein d'outils, notamment par Ollama et son framework llama.cpp.</p>
<p>Tout est préinstallé sur Fleurdelix mais si vous avez un linux différent ou Ubuntu, il faudra installer le framework llama.cpp et le compiler avec cmake.</p>
<p>J'ai fait une duplication du build de ollama avec l'ensemble de ces outils ici pour l'exemple : <strong>on utilise ici le script fournit par le framework ollama qui permet de convertir notre modèle généré avec notre python avec l'outil convert_hf_to_gguf.py</strong></p>
<p>Puisque notre modèle était finetuné dans un modèle au format Hugging Face (.safetensors), nous l'avons converti dans un modèle plus générique :</p>
<p>Avec le script Ollama, nous spécifions le répertoire où se trouve notre modèle généré au format HuggingFace et le fichier de sortie de notre modèle GGUF. Le f16 signifie que chaque poids ou paramètre du modèle est stocké en utilisant 16 bits (2 octets)</p>
<p>  <img width="1250" height="267" alt="img5" src="https://github.com/user-attachments/assets/d99672a4-c678-4c41-a07e-343b9804d226" />
</p>
<p>A l'exécution : </p>
<p>  <img width="1246" height="835" alt="img6" src="https://github.com/user-attachments/assets/ff44f5df-5dbc-4227-bf72-96ad55854c28" />
</p>
<h3><strong>Quantification du modèle (Compression pour la vitesse et la taille)</strong></h3>
<p>On veut quantifier le modèle pour que le modèle puisse s'exécuter beaucoup plus rapidement sur du matériel standard comme un cpu ou gpu on va dire "grand public" :)</p>
<p>c'est donc un processus de compression des poids d'un modèle de llm, passant d'une haute précision (16 bits) à une basse précision (4 bits). Cette technique bien connue réduit drastiquement la taille du fichier et la consommation de mémoire sans avoir d'impacts.</p>
<p>Le framework d'Ollama, ollama.cpp, à une fonction ollama_quantize permettant de réaliser cette opération. Les noyaux de calcul de llama.cpp sont hyper optimisés, cela accélère la vitesse d'inférence, cela permet d'avoir une utilisation fluide en local :)</p>
<p>On tape la commande suivante :</p>
<p><strong>./llama-quantize shellbots_modelmanagement_fp16.gguf shellbots_modelmanagement_q4_k_m.gguf Q4_K_M</strong></p>
<p>  <img width="1248" height="883" alt="img7" src="https://github.com/user-attachments/assets/46d77f31-4120-4b44-8367-508f96cdf82c" />
</p>
<p><strong>Notre modèle passe de 7Gb à 2Gb :)</strong></p>
<p><strong>Le type Q4_K_M est le format optimisé pour la quantification</strong>. Il offre un excellent équilibre entre la vitesse d'inférence / performance et la préservation de la qualité du modèle.</p>
<h3><strong>Utilisation et tests dans Ollama</strong></h3>
<p>Pour utiliser maintenant notre modèle, on va créer un ModelFile (pour définir le rôle) qui pointe vers notre modèle GGUF optimisé.</p>
<p>On va lui donner un rôle de "Manager expert". On créé le fichier ModelFile suivant : </p>
<div style="color: #cccccc; background-color: #1f1f1f; font-family: 'Droid Sans Mono', 'monospace', monospace; font-weight: normal; font-size: 8px; line-height: 4px; white-space: pre;">
<div>
<span style="color: #cccccc;">FROM .</span><span style="color: #d4d4d4;">/</span><span style="color: #9cdcfe;">llama</span><span style="color: #cccccc;">.</span><span style="color: #9cdcfe;">cpp</span><span style="color: #d4d4d4;">/</span><span style="color: #cccccc;">build</span><span style="color: #d4d4d4;">/</span><span style="color: #9cdcfe;">shellbots_modelmanagement_q4_k_m</span><span style="color: #cccccc;">.</span><span style="color: #9cdcfe;">gguf</span>
</div>
<br>
<div><span style="color: #6a9955;"># Role du modèle créé et fusionné</span></div>
<div>
<span style="color: #dcdcaa;">SYSTEM</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"""Tu es un expert en management, en leadership, et en stratégie d'entreprise. Tes réponses sont toujours</span>
</div>
<div><span style="color: #ce9178;"> concises, extrêmement professionnelles et orientées solution. Tu t'adresses à l'utilisateur comme à un </span></div>
<div><span style="color: #ce9178;"> collaborateur clé."""</span></div>
<br>
<div><span style="color: #6a9955;"># Paramètres spécifiques au modèle initial</span></div>
<div>
<span style="color: #dcdcaa;">TEMPLATE</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"""{{ if .System }}&lt;|system|&gt;</span>
</div>
<div><span style="color: #ce9178;">{{ .System }}&lt;|end|&gt;</span></div>
<div><span style="color: #ce9178;">{{ end }}{{ if .Prompt }}&lt;|user|&gt;</span></div>
<div><span style="color: #ce9178;">{{ .Prompt }}&lt;|end|&gt;</span></div>
<div><span style="color: #ce9178;">{{ end }}&lt;|assistant|&gt;</span></div>
<div><span style="color: #ce9178;">{{ .Response }}&lt;|end|&gt;"""</span></div>
<br>
<div><span style="color: #6a9955;"># Indique le jeton d'arrêt pour éviter que le modèle ne continue de générer au-delà de sa réponse</span></div>
<div>
<span style="color: #dcdcaa;">PARAMETER</span><span style="color: #cccccc;"> </span><span style="color: #dcdcaa;">stop</span><span style="color: #cccccc;"> </span><span style="color: #ce9178;">"&lt;|end|&gt;"</span>
</div>
<br>
<div><span style="color: #6a9955;"># Paramètres d'inférence (conservateurs pour la qualité)</span></div>
<div>
<span style="color: #dcdcaa;">PARAMETER</span><span style="color: #cccccc;"> </span><span style="color: #dcdcaa;">temperature</span><span style="color: #cccccc;"> </span><span style="color: #b5cea8;">0.6</span>
</div>
<div>
<span style="color: #dcdcaa;">PARAMETER</span><span style="color: #cccccc;"> </span><span style="color: #dcdcaa;">top_k</span><span style="color: #cccccc;"> </span><span style="color: #b5cea8;">40</span>
</div>
<div>
<span style="color: #dcdcaa;">PARAMETER</span><span style="color: #cccccc;"> </span><span style="color: #dcdcaa;">top_p</span><span style="color: #cccccc;"> </span><span style="color: #b5cea8;">0.9</span>
</div>
</div>
<p><br></p>
<p><strong>Ensuite, on va importer le modèle (enfin !) dans Ollama :)</strong></p>
<p>On tape la commande : <strong>ollama create shellbots-manager -f ModelFile</strong></p>
<p>  <img width="1233" height="291" alt="img8" src="https://github.com/user-attachments/assets/8ad2b549-a698-4571-9934-4b76d281b8ee" />
</p>
<p>On vérifie que notre modèle est bien dans l'écosystème de Ollama avec la commande <strong>ollama list</strong> :</p>
<p>  <img width="906" height="137" alt="img9" src="https://github.com/user-attachments/assets/aeca6f16-8cc9-4bc2-9b90-69f44b2c44a2" />
</p>
<p>Si on regarde les informations sur notre modèle, on retrouve bien notre architecture phi3 avec notre rôle bien défini :</p>
<p> <img width="1243" height="678" alt="img10" src="https://github.com/user-attachments/assets/68bf350e-02b8-4b76-9a0a-a0305d0bfd93" />
</p>
<p> <img width="1150" height="204" alt="img11" src="https://github.com/user-attachments/assets/b83734e2-01d6-4fd2-b829-d12442a5d684" />
</p>
<p>Maintenant on teste notre modèle :) on tape la commande <strong>ollama run shellbots-manager</strong></p>
<p><strong>Voici 3 prompts d'exemples. Le résultat est instanté pas d'attente de réflexion grâce à la quantisation dans ollama.</strong></p>
<p>  <img width="1238" height="817" alt="img12" src="https://github.com/user-attachments/assets/54cc6917-1a73-46da-aeb9-fd5cb868fc42" />
</p>
<p>Exemple d'utilisation en local avec OpenWebUI et notre modèle Ollama :</p>
<p>  <img width="1406" height="887" alt="img14" src="https://github.com/user-attachments/assets/5c6ecde7-a793-4270-bf80-62f6e6635090" />
</p>

<p>Si vous avez des questions, n'hésitez pas à me contacter  :)</p>
<p>Dominique</p>
<p style="margin-top: 30px; font-size: 0.9em; color: #666; font-style: italic;">L'auteur, Dominique Delaire, est consultant sénior en machine learning et créateur de fleurdelix OS, système d'exploitation conçu autour des modèles locaux et de la souveraineté des données. Les opinions exprimées n'engagent que lui.</p>
