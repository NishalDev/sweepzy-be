import os
import sys
import subprocess
import shutil

def generate_model(module_name, attributes):
    if not module_name or not attributes:
        print("❌ Usage: python generate_model.py <ModelName> <field:type,...>")
        sys.exit(1)

    print(f"🚀 Generating model: {module_name} with attributes: {attributes}")

    # Run Sequelize model generation command
    try:
        subprocess.run(f"npx sequelize-cli model:generate --name {module_name} --attributes {attributes}", shell=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Model generation failed. Ensure Sequelize CLI is installed.")
        sys.exit(1)

    # Define paths
    model_file_name = f"{module_name.lower()}.js"
    model_path = os.path.join("models", model_file_name)
    module_folder = os.path.join("api", module_name)

    # Create module directory if not exists
    os.makedirs(module_folder, exist_ok=True)

    # Move the model file
    new_model_path = os.path.join(module_folder, f"{module_name}.model.js")
    try:
        shutil.move(model_path, new_model_path)
        print(f"✅ Model moved to: {new_model_path}")
    except FileNotFoundError:
        print("❌ Model file not found. Check if Sequelize generated the model correctly.")
        sys.exit(1)

    # Run migrations
    print("🚀 Running migration...")
    try:
        subprocess.run("npm run db:migrate", shell=True, check=True)
        print("🎉 Model creation and migration completed!")
    except subprocess.CalledProcessError:
        print("❌ Migration failed. Ensure Sequelize is configured correctly.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("❌ Usage: python generate_model.py <ModelName> <field:type,...>")
        sys.exit(1)

    model_name = sys.argv[1]
    attributes = ",".join(sys.argv[2:])
    generate_model(model_name, attributes)
