#!/usr/bin/env python3
"""
JSON Schema → Pydantic Model + dataclass 自動生成ツール

Usage:
    python tools/codegen.py [--schemas-dir DIR] [--output-dir DIR] [--dry-run]
    python tools/codegen.py --validate-only
    python tools/codegen.py --generate-dataclasses
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from datamodel_code_generator import DataModelType, generate
except ImportError:
    print(
        "[codegen] Warning: datamodel-code-generator not installed. Run: pip install datamodel-code-generator"
    )
    generate = None

try:
    import jsonschema
except ImportError:
    print("[codegen] Warning: jsonschema not installed. Run: pip install jsonschema")
    jsonschema = None

try:
    import yaml
except ImportError:
    print("[codegen] Warning: pyyaml not installed. Run: pip install pyyaml")
    yaml = None


class CodeGenerator:
    def __init__(self, schemas_dir: Path, output_dir: Path, dataclasses_dir: Path):
        self.schemas_dir = schemas_dir
        self.output_dir = output_dir
        self.dataclasses_dir = dataclasses_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dataclasses_dir.mkdir(parents=True, exist_ok=True)

    def generate_pydantic_models(self, dry_run: bool = False) -> None:
        """JSON Schema → Pydantic BaseModel 生成"""
        if generate is None:
            print("[codegen] ERROR: datamodel-code-generator not available")
            return

        schema_files = list(self.schemas_dir.rglob("*.json"))
        schema_files = [f for f in schema_files if not f.name.startswith("_")]

        print(f"[codegen] Found {len(schema_files)} schema files")

        for schema_file in schema_files:
            relative = schema_file.relative_to(self.schemas_dir)
            out_file = self.output_dir / relative.with_suffix(".py")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                if dry_run:
                    print(f"[codegen] Would generate: {out_file}")
                else:
                    generate(
                        input_=schema_file.read_text(encoding="utf-8"),
                        input_filename=str(schema_file),
                        output_model_type=DataModelType.PydanticV2BaseModel,
                        output=str(out_file),
                        base_class="data.schemas._base.DataModel",
                        field_constraints=True,
                        snake_case_field=False,
                        use_standard_collections=True,
                        use_schema_description=True,
                        use_field_description=True,
                        disable_timestamp=True,
                        allow_private_network=True,
                    )
                    print(f"[codegen] Generated: {out_file}")
            except Exception as e:
                print(f"[codegen] ERROR generating {schema_file}: {e}")

    def validate_schemas(self) -> int:
        """全スキーマの構文検証"""
        if jsonschema is None:
            print("[codegen] ERROR: jsonschema not available")
            return 1

        errors = 0
        for schema_file in self.schemas_dir.rglob("*.json"):
            if schema_file.name.startswith("_"):
                continue
            try:
                schema = json.loads(schema_file.read_text(encoding="utf-8"))
                # メタスキーマで検証
                jsonschema.Draft7Validator.check_schema(schema)
                print(f"[validate] OK: {schema_file.relative_to(self.schemas_dir)}")
            except Exception as e:
                print(
                    f"[validate] ERROR: {schema_file.relative_to(self.schemas_dir)} - {e}"
                )
                errors += 1
        return errors

    def validate_data_files(self, data_dir: Path) -> int:
        """YAMLデータファイルをスキーマで検証"""
        if jsonschema is None or yaml is None:
            print("[codegen] ERROR: jsonschema or pyyaml not available")
            return 1

        errors = 0
        data_files = list(data_dir.glob("*.yaml")) + list(data_dir.glob("*.yml"))

        for data_file in data_files:
            # 対応するスキーマを推測
            schema_name = data_file.stem
            schema_file = self.schemas_dir / f"{schema_name}.json"
            if not schema_file.exists():
                # サブディレクトリも探す
                for subdir in self.schemas_dir.iterdir():
                    if subdir.is_dir():
                        sf = subdir / f"{schema_name}.json"
                        if sf.exists():
                            schema_file = sf
                            break
                        # 単数形も試す (items.yaml -> item/item.json)
                        singular = schema_name.rstrip("s")
                        sf = subdir / f"{singular}.json"
                        if sf.exists():
                            schema_file = sf
                            break

            if not schema_file.exists():
                print(f"[validate] SKIP (no schema): {data_file.name}")
                continue

            try:
                with open(data_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                with open(schema_file, encoding="utf-8") as f:
                    schema = json.load(f)

                # まず全体を検証
                try:
                    jsonschema.validate(data, schema)
                except jsonschema.ValidationError as e:
                    # 全体検証失敗時、ドキュメントスキーマかコレクションスキーマか判定
                    is_doc_schema = False
                    if isinstance(data, dict) and isinstance(schema, dict):
                        required = schema.get("required", [])
                        if required and all(r in data for r in required):
                            # 必須プロパティが全て存在する -> ドキュメントスキーマ
                            is_doc_schema = True

                    if not is_doc_schema and isinstance(data, dict):
                        # コレクションスキーマ: 各エントリを検証
                        for key, value in data.items():
                            try:
                                jsonschema.validate(value, schema)
                            except jsonschema.ValidationError as e2:
                                print(
                                    f"[validate] ERROR: {data_file.name}[{key}] - {e2.message}"
                                )
                                errors += 1
                    else:
                        # ドキュメントスキーマ: エラーを出力
                        print(f"[validate] ERROR: {data_file.name} - {e.message}")
                        errors += 1

                print(f"[validate] OK: {data_file.name}")
            except Exception as e:
                print(f"[validate] ERROR: {data_file.name} - {e}")
                errors += 1
        return errors

    def generate_dataclasses(self, dry_run: bool = False) -> None:
        """Pydanticモデルから frozen dataclass (slots=True) 生成"""
        if not self.output_dir.exists():
            print("[codegen] No Pydantic models found. Run generation first.")
            return

        import importlib.util

        # 生成されたモジュールをインポート
        sys.path.insert(0, str(self.output_dir.parent))

        py_files = list(self.output_dir.rglob("*.py"))
        py_files = [f for f in py_files if not f.name.startswith("_")]

        for py_file in py_files:
            try:
                module_name = f"data.generated.{py_file.relative_to(self.output_dir).with_suffix('').as_posix().replace('/', '.')}"
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in module.__dict__.items():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, module.DataModel)
                        and obj is not module.DataModel
                    ):
                        dc_code = self._generate_dataclass_code(name, obj)
                        out_file = self.dataclasses_dir / py_file.relative_to(
                            self.output_dir
                        ).with_suffix(".py")
                        out_file.parent.mkdir(parents=True, exist_ok=True)

                        if dry_run:
                            print(f"[codegen] Would generate dataclass: {out_file}")
                        else:
                            # 既存ファイルに追記モードで書き込み
                            self._append_dataclass(out_file, dc_code)
                            print(f"[codegen] Generated dataclass: {out_file}")

            except Exception as e:
                print(f"[codegen] ERROR generating dataclass for {py_file}: {e}")

    def _generate_dataclass_code(self, model_name: str, model_class: type) -> str:
        """Pydanticモデルから dataclass コード生成"""
        fields = model_class.model_fields
        lines = []

        # インポート
        imports = set()
        for field_name, field_info in fields.items():
            ann = field_info.annotation
            if ann:
                imports.add(self._type_to_import(ann))

        lines.append("from __future__ import annotations")
        lines.append("from dataclasses import dataclass")
        lines.append("from typing import Optional, List, Dict, Any, Union, Literal")
        for imp in sorted(imports):
            lines.append(imp)
        lines.append(
            "from data.schemas._base import DataClassBase, EffectData, PrerequisiteData, RewardData, ObjectiveData, DropEntryData"
        )
        lines.append("")

        # dataclass 定義
        lines.append("@dataclass(frozen=True, slots=True)")
        lines.append(f"class {model_name}(DataClassBase):")

        for field_name, field_info in fields.items():
            ann = field_info.annotation
            if ann:
                type_str = self._annotation_to_str(ann)
            else:
                type_str = "Any"

            default = field_info.default
            if default is not None and default != ...:
                if isinstance(default, str):
                    default_str = f'"{default}"'
                else:
                    default_str = str(default)
                lines.append(f"    {field_name}: {type_str} = {default_str}")
            elif field_info.is_required():
                lines.append(f"    {field_name}: {type_str}")
            else:
                lines.append(f"    {field_name}: Optional[{type_str}] = None")

        lines.append("")
        return "\n".join(lines)

    def _type_to_import(self, ann: Any) -> str:
        """型アノテーションから必要なインポートを推測"""
        ann_str = str(ann)
        if (
            "Optional" in ann_str
            or "Union" in ann_str
            or "List" in ann_str
            or "Dict" in ann_str
        ):
            return "from typing import Optional, Union, List, Dict"
        if "Literal" in ann_str:
            return "from typing import Literal"
        return ""

    def _annotation_to_str(self, ann: Any) -> str:
        """型アノテーションを文字列に変換"""
        return str(ann).replace("typing.", "").replace("pydantic.types.", "")

    def _append_dataclass(self, out_file: Path, dc_code: str) -> None:
        """dataclassコードをファイルに追記（重複防止）"""
        existing = ""
        if out_file.exists():
            existing = out_file.read_text(encoding="utf-8")

        # クラス名を抽出
        class_name = None
        for line in dc_code.split("\n"):
            if line.startswith("class "):
                class_name = line.split()[1].split("(")[0]
                break

        if class_name and f"class {class_name}" in existing:
            # 既存クラスを置換
            import re

            pattern = rf"@dataclass\(frozen=True, slots=True\)\nclass {class_name}\(.*?\):\n(?:    .*\n)*"
            existing = re.sub(pattern, dc_code + "\n", existing, flags=re.DOTALL)
        else:
            existing += "\n\n" + dc_code

        out_file.write_text(existing, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="naRou Data Schema Code Generator")
    parser.add_argument(
        "--schemas-dir", default="data/schemas", help="JSON Schema directory"
    )
    parser.add_argument(
        "--output-dir", default="data/generated", help="Pydantic output directory"
    )
    parser.add_argument(
        "--dataclasses-dir",
        default="data/generated_dc",
        help="dataclass output directory",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without writing"
    )
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate schemas"
    )
    parser.add_argument(
        "--validate-data",
        action="store_true",
        help="Validate data files against schemas",
    )
    parser.add_argument(
        "--generate-dataclasses",
        action="store_true",
        help="Generate frozen dataclasses from Pydantic models",
    )
    parser.add_argument(
        "--data-dir", default="data", help="Data directory for validation"
    )

    args = parser.parse_args()

    schemas_dir = Path(args.schemas_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    dataclasses_dir = Path(args.dataclasses_dir).resolve()
    data_dir = Path(args.data_dir).resolve()

    if not schemas_dir.exists():
        print(f"[codegen] ERROR: Schemas directory not found: {schemas_dir}")
        return 1

    generator = CodeGenerator(schemas_dir, output_dir, dataclasses_dir)

    if args.validate_only:
        return generator.validate_schemas()

    if args.validate_data:
        return generator.validate_data_files(data_dir)

    if args.generate_dataclasses:
        generator.generate_dataclasses(dry_run=args.dry_run)
        return 0

    # デフォルト: Pydanticモデル生成
    generator.generate_pydantic_models(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
