# T-Shirt Image Workflow

Automates the full pipeline from raw garment photos to multi-pose fashion renders using [Higgsfield AI](https://higgsfield.ai).

## Workflow

| Step | What happens |
|------|-------------|
| 1 | Scan `tshirts/` for design folders |
| 2 | Pick the raw t-shirt image from each folder |
| 3 | Upload raw image to Higgsfield |
| 4 | Apply generation prompt |
| 5 | Generate a base model image wearing the t-shirt |
| 6 | Download the result and re-upload it to Higgsfield |
| 7 | Generate multiple pose variations |
| 8 | Save all images into a named output folder |

## Folder structure

```
tshirts/                  <- put your design folders here
  design_01/
    raw.jpg               <- one raw t-shirt image per folder
  design_02/
    raw.png

output/                   <- generated automatically
  design_01/
    base_model_1.jpg
    pose_1_front_view_standing_straight.jpg
    pose_2_side_view_walking_pose.jpg
    ...
  design_02/
    ...
```

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Higgsfield API key
cp .env.example .env
# edit .env and paste your key

# 3. Add your t-shirt folders under tshirts/
```

## Run

```bash
# Process all designs
python workflow.py

# Custom config
python workflow.py --config my_config.yaml

# Override input/output directories
python workflow.py --input my_tshirts/ --output results/

# Process a single design
python workflow.py --design design_01
```

## Configuration (`config.yaml`)

| Key | Description |
|-----|-------------|
| `input_dir` | Folder containing design sub-folders |
| `output_dir` | Root folder for generated images |
| `generation_prompt` | Prompt for base model generation (step 5) |
| `num_base_images` | How many base images to generate per design |
| `poses` | List of pose descriptions for step 7 |
| `poll_interval_seconds` | How often to check job status |
| `job_timeout_seconds` | Max wait time per job |
