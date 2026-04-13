# -*- coding: utf-8 -*-
"""
カテゴリ特記事項・スキル名マスタ（config.json）。

category_master[<カテゴリ名JP>].special_notes: list[dict]
  - kind: "required" | "recommended" | "memo"
  - メモ: memo_jp, memo_en
  - 必要/推奨: detail_kind "level"|"skill_level"|"equipment"|"skill"
      level: level (int)
      skill_level: skill_id, skill_level_value (int)
      equipment: equipment_name_jp, equipment_name_en（旧 equipment_name は JP として読込）
      skill: skill_id

skill_name_master: list[{"id","name_jp","name_en"}]
"""
from __future__ import annotations

import json
import random
import re
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

KIND_REQUIRED = "required"
KIND_REQUIRED_LENIENT = "required_lenient"
KIND_RECOMMENDED = "recommended"
KIND_MEMO = "memo"

DETAIL_LEVEL = "level"
DETAIL_SKILL_LEVEL = "skill_level"
DETAIL_EQUIPMENT = "equipment"
DETAIL_SKILL = "skill"

_KIND_JP_TO_ID = {
    "必要条件": KIND_REQUIRED,
    "必要条件（やや緩め）": KIND_REQUIRED_LENIENT,
    "推奨条件": KIND_RECOMMENDED,
    "メモ": KIND_MEMO,
}
_KIND_ID_TO_JP = {v: k for k, v in _KIND_JP_TO_ID.items()}

_DETAIL_JP_TO_ID = {
    "レベル": DETAIL_LEVEL,
    "スキルレベル": DETAIL_SKILL_LEVEL,
    "装備": DETAIL_EQUIPMENT,
    "スキル": DETAIL_SKILL,
}
_DETAIL_ID_TO_JP = {v: k for k, v in _DETAIL_JP_TO_ID.items()}


def ensure_skill_master_list(config: dict) -> List[dict]:
    raw = config.get("skill_name_master")
    if not isinstance(raw, list):
        config["skill_name_master"] = []
    return config["skill_name_master"]


def skill_options_for_combobox(config: dict) -> tuple[List[str], Dict[str, str]]:
    """表示ラベル一覧と label -> skill_id。"""
    labels: List[str] = []
    label_to_id: Dict[str, str] = {}
    for it in ensure_skill_master_list(config):
        if not isinstance(it, dict):
            continue
        sid = (it.get("id") or "").strip()
        if not sid:
            continue
        jp = (it.get("name_jp") or "").strip()
        en = (it.get("name_en") or "").strip()
        lab = jp or sid
        if en:
            lab = f"{lab}  ({en})"
        if lab in label_to_id:
            lab = f"{lab}  [{sid}]"
        labels.append(lab)
        label_to_id[lab] = sid
    return labels, label_to_id


def new_skill_id(existing_ids: set) -> str:
    for _ in range(50):
        cand = f"SKILL_{random.randint(10000, 99999)}"
        if cand not in existing_ids:
            return cand
    return f"SKILL_{random.randint(100000, 999999)}"


def save_editor_config(editor) -> None:
    with open(editor.config_path, "w", encoding="utf-8") as f:
        json.dump(editor.config, f, indent=4, ensure_ascii=False)
    editor.reload_config()


class SkillNameMasterWindow(ctk.CTkToplevel):
    """スキル名マスタ（JP/EN・安定 ID）。設定メニューまたは特記事項ウィンドウから開く。"""

    def __init__(self, editor, on_saved: Optional[Callable[[], None]] = None):
        super().__init__(editor)
        self.editor = editor
        self._on_saved = on_saved
        self.title("スキル名マスタ")
        self.geometry("720x520")
        self.transient(editor)
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        ctk.CTkLabel(
            self,
            text="スキル名マスタ（特記事項の「スキル」「スキルレベル」から参照）",
            font=("Meiryo", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            self,
            text="各行: 表示名(JP)・(EN)。ID は保存時に未設定なら自動採番されます。",
            font=("Meiryo", 10),
            text_color="#888888",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        scroll = ctk.CTkScrollableFrame(self, fg_color="#2b2b2b")
        scroll.pack(fill="both", expand=True, padx=12, pady=4)
        self._scroll = scroll
        self._rows: List[Dict[str, Any]] = []

        self._load_from_config()
        if not self._rows:
            self._add_empty_row()

        f_btn = ctk.CTkFrame(self, fg_color="transparent")
        f_btn.pack(fill="x", padx=12, pady=10)
        ctk.CTkButton(f_btn, text="＋ 行を追加", command=self._add_empty_row, fg_color="#3498db").pack(side="left", padx=4)
        ctk.CTkButton(f_btn, text="保存", command=self._save, fg_color="#27ae60", width=100).pack(side="right", padx=4)
        ctk.CTkButton(f_btn, text="閉じる", command=self.destroy, fg_color="#7f8c8d", width=100).pack(side="right", padx=4)

    def _load_from_config(self):
        ensure_skill_master_list(self.editor.config)
        for it in self.editor.config["skill_name_master"]:
            if not isinstance(it, dict):
                continue
            self._append_row_ui(it.get("id", "").strip(), it.get("name_jp", ""), it.get("name_en", ""))

    def _append_row_ui(self, sid: str, jp: str, en: str):
        f = ctk.CTkFrame(self._scroll, fg_color="#333333", corner_radius=6)
        f.pack(fill="x", pady=4, padx=4)
        ctk.CTkLabel(f, text="ID", width=40, anchor="w", text_color="#888888").grid(row=0, column=0, padx=6, pady=4, sticky="w")
        lbl_id = ctk.CTkLabel(f, text=sid or "（自動）", width=120, anchor="w", text_color="#aaaaaa")
        lbl_id.grid(row=0, column=1, padx=4, pady=4, sticky="w")
        ctk.CTkLabel(f, text="JP", width=32, anchor="w").grid(row=0, column=2, padx=4, pady=4, sticky="w")
        e_jp = ctk.CTkEntry(f, width=200)
        e_jp.insert(0, jp)
        e_jp.grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(f, text="EN", width=32, anchor="w").grid(row=0, column=4, padx=4, pady=4, sticky="w")
        e_en = ctk.CTkEntry(f, width=200)
        e_en.insert(0, en)
        e_en.grid(row=0, column=5, padx=4, pady=4, sticky="ew")
        f.grid_columnconfigure(3, weight=1)
        f.grid_columnconfigure(5, weight=1)

        def remove():
            f.destroy()
            self._rows = [x for x in self._rows if x["frame"] is not f]

        ctk.CTkButton(f, text="削除", width=56, fg_color="#c0392b", command=remove).grid(row=0, column=6, padx=8, pady=4)
        self._rows.append({"frame": f, "id": sid, "lbl_id": lbl_id, "jp": e_jp, "en": e_en})

    def _add_empty_row(self):
        self._append_row_ui("", "", "")

    def _save(self):
        seen: set = set()
        out: List[dict] = []
        for r in self._rows:
            try:
                if not r["frame"].winfo_exists():
                    continue
            except tk.TclError:
                continue
            jp = r["jp"].get().strip()
            en = r["en"].get().strip()
            sid = (r["id"] or "").strip()
            if not jp and not en and not sid:
                continue
            if not sid:
                sid = new_skill_id(seen)
            if sid in seen:
                messagebox.showerror("エラー", f"ID が重複しています: {sid}")
                return
            seen.add(sid)
            out.append({"id": sid, "name_jp": jp, "name_en": en})
        self.editor.config["skill_name_master"] = out
        try:
            save_editor_config(self.editor)
        except Exception as e:
            messagebox.showerror("保存エラー", str(e))
            return
        messagebox.showinfo("保存", "スキル名マスタを保存しました。")
        if self._on_saved:
            self._on_saved()
        self.destroy()


class SpecialNoteBlock(ctk.CTkFrame):
    """1件分の特記事項編集ブロック。"""

    def __init__(self, master, config: dict, data: Optional[dict] = None, **kwargs):
        fg = kwargs.pop("fg_color", "#2f2f2f")
        super().__init__(master, fg_color=fg, corner_radius=8, **kwargs)
        self._config_ref = config
        self._detail_widgets: Dict[str, Any] = {}
        self._pending_seed: Optional[dict] = None

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(top, text="タイプ", width=72, anchor="w").pack(side="left", padx=(0, 6))
        init_k = KIND_MEMO
        if data and isinstance(data, dict):
            init_k = data.get("kind") or KIND_MEMO
        init_jp = _KIND_ID_TO_JP.get(init_k, "メモ")
        self._cmb_kind = ctk.CTkComboBox(top, values=list(_KIND_JP_TO_ID.keys()), width=168)
        self._cmb_kind.set(init_jp)
        self._cmb_kind.pack(side="left", padx=4)
        def_on = True
        if data and isinstance(data, dict) and "default_enabled" in data:
            def_on = bool(data.get("default_enabled"))
        self._def_var = tk.BooleanVar(value=def_on)
        self._chk_default = ctk.CTkCheckBox(
            top, text="新規ピンで既定ON", variable=self._def_var, width=140, font=("Meiryo", 10),
        )
        self._chk_default.pack(side="left", padx=(8, 4))

        self._detail_host = ctk.CTkFrame(self, fg_color="transparent")
        self._detail_host.pack(fill="x", padx=8, pady=(0, 8))

        def on_kind(_=None):
            self._rebuild_detail(self._current_kind(), None)

        self._cmb_kind.configure(command=lambda v: on_kind())
        self._rebuild_detail(init_k, data if isinstance(data, dict) else None)

    def _current_kind(self) -> str:
        return _KIND_JP_TO_ID.get(self._cmb_kind.get(), KIND_MEMO)

    def _rebuild_detail(self, kind: str, data: Optional[dict] = None):
        for w in self._detail_host.winfo_children():
            w.destroy()
        self._detail_widgets.clear()
        if kind == KIND_MEMO:
            ctk.CTkLabel(self._detail_host, text="メモ（JP）").pack(anchor="w", padx=2, pady=(4, 0))
            tj = ctk.CTkTextbox(self._detail_host, height=72)
            tj.pack(fill="x", padx=2, pady=2)
            mj = (data or {}).get("memo_jp", "") if data else ""
            tj.insert("1.0", mj)
            ctk.CTkLabel(self._detail_host, text="メモ（EN）").pack(anchor="w", padx=2, pady=(6, 0))
            te = ctk.CTkTextbox(self._detail_host, height=72)
            te.pack(fill="x", padx=2, pady=2)
            me = (data or {}).get("memo_en", "") if data else ""
            te.insert("1.0", me)
            self._detail_widgets = {"memo_jp": tj, "memo_en": te}
            return

        ctk.CTkLabel(self._detail_host, text="条件の種類", anchor="w").pack(anchor="w", padx=2, pady=(4, 0))
        init_d = DETAIL_LEVEL
        if data and isinstance(data, dict):
            init_d = data.get("detail_kind") or DETAIL_LEVEL
        init_d_jp = _DETAIL_ID_TO_JP.get(init_d, "レベル")
        cmb_d = ctk.CTkComboBox(self._detail_host, values=list(_DETAIL_JP_TO_ID.keys()), width=160)
        cmb_d.set(init_d_jp)
        cmb_d.pack(anchor="w", padx=2, pady=4)
        self._detail_widgets["detail_cmb"] = cmb_d

        inner = ctk.CTkFrame(self._detail_host, fg_color="transparent")
        inner.pack(fill="x", padx=2, pady=4)

        self._pending_seed = data

        def refill_inner(_=None):
            for w in inner.winfo_children():
                w.destroy()
            dk = _DETAIL_JP_TO_ID.get(cmb_d.get(), DETAIL_LEVEL)
            seed = self._pending_seed
            self._pending_seed = None
            self._fill_conditional_inner(inner, dk, seed)

        cmb_d.configure(command=lambda v: refill_inner())
        refill_inner()

    def _fill_conditional_inner(self, inner, detail_kind: str, data: Optional[dict]):
        data = data or {}
        labels, l2i = skill_options_for_combobox(self._config_ref)
        if detail_kind == DETAIL_LEVEL:
            ctk.CTkLabel(inner, text="レベル（数値）").pack(anchor="w")
            ent = ctk.CTkEntry(inner, width=120)
            lv = data.get("level", "")
            ent.insert(0, str(lv) if lv != "" and lv is not None else "")
            ent.pack(anchor="w", pady=2)
            self._detail_widgets["level_ent"] = ent
            return
        if detail_kind == DETAIL_SKILL_LEVEL:
            ctk.CTkLabel(inner, text="スキル").pack(anchor="w")
            cmb = ctk.CTkComboBox(inner, values=labels or ["（マスタにスキルがありません）"], width=320)
            sid = (data.get("skill_id") or "").strip()
            sel_lab = None
            for lab, i in l2i.items():
                if i == sid:
                    sel_lab = lab
                    break
            if sel_lab:
                cmb.set(sel_lab)
            elif labels:
                cmb.set(labels[0])
            cmb.pack(anchor="w", pady=2)
            ctk.CTkLabel(inner, text="スキルレベル（数値）").pack(anchor="w", pady=(6, 0))
            ent_lv = ctk.CTkEntry(inner, width=120)
            sv = data.get("skill_level_value", data.get("skill_level", ""))
            ent_lv.insert(0, str(sv) if sv != "" and sv is not None else "")
            ent_lv.pack(anchor="w", pady=2)
            self._detail_widgets["sl_cmb"] = cmb
            self._detail_widgets["sl_lv"] = ent_lv
            self._detail_widgets["_l2i_sl"] = l2i
            return
        if detail_kind == DETAIL_EQUIPMENT:
            legacy = (data.get("equipment_name") or "").strip()
            jp0 = (data.get("equipment_name_jp") or legacy or "").strip()
            en0 = (data.get("equipment_name_en") or "").strip()
            ctk.CTkLabel(inner, text="装備名（日本語）").pack(anchor="w")
            ent_jp = ctk.CTkEntry(inner, width=360)
            ent_jp.insert(0, jp0)
            ent_jp.pack(fill="x", pady=2)
            self._detail_widgets["eq_ent_jp"] = ent_jp
            ctk.CTkLabel(inner, text="装備名（English）").pack(anchor="w", pady=(6, 0))
            ent_en = ctk.CTkEntry(inner, width=360)
            ent_en.insert(0, en0)
            ent_en.pack(fill="x", pady=2)
            self._detail_widgets["eq_ent_en"] = ent_en
            return
        if detail_kind == DETAIL_SKILL:
            ctk.CTkLabel(inner, text="スキル").pack(anchor="w")
            cmb = ctk.CTkComboBox(inner, values=labels or ["（マスタにスキルがありません）"], width=320)
            sid = (data.get("skill_id") or "").strip()
            sel_lab = None
            for lab, i in l2i.items():
                if i == sid:
                    sel_lab = lab
                    break
            if sel_lab:
                cmb.set(sel_lab)
            elif labels:
                cmb.set(labels[0])
            cmb.pack(anchor="w", pady=2)
            self._detail_widgets["sk_cmb"] = cmb
            self._detail_widgets["_l2i_sk"] = l2i
            return

    def to_dict(self) -> Optional[dict]:
        kind = self._current_kind()
        if kind == KIND_MEMO:
            tj = self._detail_widgets.get("memo_jp")
            te = self._detail_widgets.get("memo_en")
            if not tj or not te:
                return None
            return {
                "kind": KIND_MEMO,
                "memo_jp": tj.get("1.0", "end-1c").strip(),
                "memo_en": te.get("1.0", "end-1c").strip(),
                "default_enabled": bool(self._def_var.get()),
            }
        cmb_d = self._detail_widgets.get("detail_cmb")
        if not cmb_d:
            return None
        dk = _DETAIL_JP_TO_ID.get(cmb_d.get(), DETAIL_LEVEL)
        out: Dict[str, Any] = {"kind": kind, "detail_kind": dk, "default_enabled": bool(self._def_var.get())}
        if dk == DETAIL_LEVEL:
            ent = self._detail_widgets.get("level_ent")
            if not ent:
                return None
            raw = ent.get().strip()
            try:
                out["level"] = int(raw) if raw else 0
            except ValueError:
                messagebox.showerror("入力エラー", "レベルは整数で入力してください。")
                return None
            return out
        if dk == DETAIL_SKILL_LEVEL:
            cmb = self._detail_widgets.get("sl_cmb")
            ent_lv = self._detail_widgets.get("sl_lv")
            l2i = self._detail_widgets.get("_l2i_sl") or {}
            if not cmb or not ent_lv:
                return None
            lab = cmb.get()
            sid = l2i.get(lab, "")
            if not sid and "（マスタ" not in lab:
                pass
            raw = ent_lv.get().strip()
            try:
                lv = int(raw) if raw else 0
            except ValueError:
                messagebox.showerror("入力エラー", "スキルレベルは整数で入力してください。")
                return None
            if not sid:
                messagebox.showerror("入力エラー", "スキルを選択してください（スキル名マスタを登録してください）。")
                return None
            out["skill_id"] = sid
            out["skill_level_value"] = lv
            return out
        if dk == DETAIL_EQUIPMENT:
            ent_jp = self._detail_widgets.get("eq_ent_jp")
            ent_en = self._detail_widgets.get("eq_ent_en")
            if not ent_jp or not ent_en:
                return None
            out["equipment_name_jp"] = ent_jp.get().strip()
            out["equipment_name_en"] = ent_en.get().strip()
            return out
        if dk == DETAIL_SKILL:
            cmb = self._detail_widgets.get("sk_cmb")
            l2i = self._detail_widgets.get("_l2i_sk") or {}
            if not cmb:
                return None
            lab = cmb.get()
            sid = l2i.get(lab, "")
            if not sid:
                messagebox.showerror("入力エラー", "スキルを選択してください（スキル名マスタを登録してください）。")
                return None
            out["skill_id"] = sid
            return out
        return out


class CategorySpecialNotesWindow(ctk.CTkToplevel):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.title("カテゴリ特記事項")
        self.geometry("820x640")
        self.transient(editor)
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        ctk.CTkLabel(self, text="カテゴリ特記事項", font=("Meiryo", 14, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        ctk.CTkLabel(
            self,
            text="カテゴリごとに「必要条件」「必要条件（やや緩め）」「推奨条件」「メモ」を登録します。"
            "「新規ピンで既定ON」はピン編集のチェック初期値です。保存時に category_special_rules へ同期されます。",
            font=("Meiryo", 10),
            text_color="#888888",
            wraplength=780,
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(bar, text="カテゴリ", width=72, anchor="w").pack(side="left", padx=(0, 6))
        cats = list((editor.config.get("category_master") or {}).keys())
        if not cats:
            cats = list(editor.category_list or [])
        self._cmb_cat = ctk.CTkComboBox(bar, values=cats or ["（カテゴリがありません）"], width=280)
        if cats:
            self._cmb_cat.set(cats[0])
        self._cmb_cat.pack(side="left", padx=4)
        self._cmb_cat.configure(command=lambda v: self._reload_notes_for_category())

        ctk.CTkButton(
            bar,
            text="スキル名マスタ…",
            width=140,
            fg_color="#8e44ad",
            command=self._open_skill_master,
        ).pack(side="left", padx=12)
        ctk.CTkButton(
            bar,
            text="カテゴリ一覧を更新",
            width=140,
            fg_color="#566573",
            command=self._refresh_category_combo,
        ).pack(side="left", padx=4)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="#2b2b2b")
        self._scroll.pack(fill="both", expand=True, padx=12, pady=8)
        self._note_rows: List[Dict[str, Any]] = []

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=12, pady=10)
        ctk.CTkButton(foot, text="＋ 特記事項を追加", command=self._add_block, fg_color="#3498db").pack(side="left", padx=4)
        ctk.CTkButton(foot, text="保存", command=self._save, fg_color="#27ae60", width=100).pack(side="right", padx=4)
        ctk.CTkButton(foot, text="閉じる", command=self.destroy, fg_color="#7f8c8d", width=100).pack(side="right", padx=4)

        self._reload_notes_for_category()

    def _refresh_category_combo(self):
        """マスタ管理保存後など、config 上のカテゴリキーを取り直す。"""
        cats = list((self.editor.config.get("category_master") or {}).keys())
        if not cats:
            cats = list(getattr(self.editor, "category_list", None) or [])
        ph = "（カテゴリがありません）"
        vals = cats if cats else [ph]
        prev = self._cmb_cat.get()
        self._cmb_cat.configure(values=vals)
        if prev in vals:
            self._cmb_cat.set(prev)
        elif vals and vals[0] != ph:
            self._cmb_cat.set(vals[0])
        else:
            self._cmb_cat.set(ph)
        self._reload_notes_for_category()

    def _clear_blocks(self):
        for nr in self._note_rows:
            try:
                nr["row"].destroy()
            except tk.TclError:
                pass
        self._note_rows.clear()

    def _current_category(self) -> str:
        return self._cmb_cat.get().strip()

    def _reload_notes_for_category(self):
        self._clear_blocks()
        cat = self._current_category()
        if not cat or cat.startswith("（"):
            return
        cm = self.editor.config.get("category_master") or {}
        info = cm.get(cat)
        if not isinstance(info, dict):
            return
        notes = info.get("special_notes")
        if not isinstance(notes, list):
            return
        for note in notes:
            if isinstance(note, dict):
                self._add_block(dict(note))

    def _add_block(self, data: Optional[dict] = None):
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", pady=6)
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        block = SpecialNoteBlock(left, self.editor.config, data=data)
        block.pack(fill="x", expand=True)

        def remove():
            try:
                row.destroy()
            except tk.TclError:
                pass
            self._note_rows = [x for x in self._note_rows if x.get("row") is not row]

        ctk.CTkButton(row, text="削除", width=52, fg_color="#c0392b", command=remove).pack(side="right", padx=4, pady=4)
        self._note_rows.append({"row": row, "block": block})

    def _open_skill_master(self):
        SkillNameMasterWindow(self.editor, on_saved=self._refresh_skill_dependent_ui)

    def _refresh_skill_dependent_ui(self):
        """スキルマスタ更新後、開いている条件 UI を取り直す。"""
        cat = self._current_category()
        self._clear_blocks()
        cm = self.editor.config.get("category_master") or {}
        info = cm.get(cat)
        notes = info.get("special_notes") if isinstance(info, dict) else []
        if isinstance(notes, list):
            for note in notes:
                if isinstance(note, dict):
                    self._add_block(dict(note))

    def _save(self):
        cat = self._current_category()
        if not cat or cat.startswith("（"):
            messagebox.showwarning("確認", "カテゴリを選択してください。")
            return
        notes_out: List[dict] = []
        for nr in self._note_rows:
            b = nr.get("block")
            if b is None:
                continue
            try:
                if not b.winfo_exists():
                    continue
            except tk.TclError:
                continue
            d = b.to_dict()
            if d is None:
                return
            notes_out.append(d)
        cm = self.editor.config.setdefault("category_master", {})
        entry = cm.get(cat)
        if not isinstance(entry, dict):
            entry = {
                "id": re.sub(r"[^\w\u3040-\u9fff]", "_", cat)[:40] or "cat",
                "name_jp": cat,
                "name_en": "",
                "type": "loot",
                "input_type": "item_select",
                "show_qty": True,
            }
            cm[cat] = entry
        entry["special_notes"] = notes_out
        try:
            from . import category_special_rules_builder as _csrb

            _csrb.sync_category_special_rules_from_master(self.editor.config)
            save_editor_config(self.editor)
        except Exception as e:
            messagebox.showerror("保存エラー", str(e))
            return
        messagebox.showinfo("保存", f"「{cat}」の特記事項を保存しました。")
        self._refresh_category_combo()
