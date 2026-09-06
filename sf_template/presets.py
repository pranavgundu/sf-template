"""Dependency profiles for generated projects."""

SCIENTIFIC = ["numpy>=1.26", "scipy>=1.12", "matplotlib>=3.8"]
ANALYTICS = SCIENTIFIC + ["pandas>=2.2", "seaborn>=0.13", "statsmodels>=0.14", "openpyxl>=3.1"]
ML = SCIENTIFIC + ["pandas>=2.2", "seaborn>=0.13"]
PACKAGES = {
    "general": SCIENTIFIC + ["pandas>=2.2", "seaborn>=0.13"],
    "science": SCIENTIFIC,
    "engineering": SCIENTIFIC + ["sympy>=1.12"],
    "computational": SCIENTIFIC + ["sympy>=1.12", "networkx>=3.2"],
    "data-analysis": ANALYTICS,
    "data-analytics": ANALYTICS,
    "observational": ANALYTICS,
    "replication": SCIENTIFIC,
    "literature-review": ["pandas>=2.2", "bibtexparser>=1.4,<2"],
    "ml": ML,
    "computer-vision": ML + ["pillow>=10", "torchvision>=0.21"],
    "nlp": ML + ["transformers>=4.45", "datasets>=3", "evaluate>=0.4"],
}
FRAMEWORKS = {
    "sklearn": ["scikit-learn>=1.5"],
    "torch": ["torch>=2.6", "lightning>=2.5"],
    "jax": ["jax>=0.4.35", "flax>=0.10", "optax>=0.2"],
}
ADDONS = {
    "notebooks": ["jupyterlab>=4", "ipykernel>=6"],
    "tracking": ["wandb>=0.19"],
    "config": ["hydra-core>=1.3,<2"],
}


def dependencies(starter, framework=None, addons=()):
    if starter not in PACKAGES:
        raise ValueError(f"Unknown starter: {starter}")
    if framework is not None and starter != "ml":
        raise ValueError("--framework applies to the ml starter; vision and NLP use torch.")
    if framework is not None and framework not in FRAMEWORKS:
        raise ValueError(f"Unknown framework: {framework}")
    selected = framework or ("torch" if starter in ("computer-vision", "nlp") else "sklearn" if starter == "ml" else None)
    packages = list(PACKAGES[starter])
    if selected:
        packages.extend(FRAMEWORKS[selected])
    for addon in addons:
        if addon not in ADDONS:
            raise ValueError(f"Unknown add-on: {addon}")
        packages.extend(ADDONS[addon])
    return sorted(set(packages)), selected
