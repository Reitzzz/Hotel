import ctypes
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
RECORD_FILE_PREFIX = "hotel_stay_records"
DEFAULT_YEAR = "2025"
CURRENT_YEAR = str(date.today().year)

HEADERS = ["名称", "入住时间", "间夜", "房型", "总价", "积分", "备注"]
OLD_HEADERS = ["酒店名称", "日期", "间夜", "房型", "费用1", "费用2 / 报销", "备注"]
AVG_HEADERS = ["名称", "入住时间", "间夜", "房型", "总价", "均价", "积分", "备注"]
DATE_RE = re.compile(r"^\d{1,2}\.\d{1,2}-\d{1,2}\.\d{1,2}$")
NIGHTS_RE = re.compile(r"^\d+间夜$")

FONT_FAMILY = "Microsoft YaHei UI"
BODY_FONT = (FONT_FAMILY, 11)
SMALL_FONT = (FONT_FAMILY, 10)
TITLE_FONT = (FONT_FAMILY, 19, "bold")
TABLE_FONT = (FONT_FAMILY, 11)
TABLE_HEADER_FONT = (FONT_FAMILY, 11, "bold")
DEFAULT_WINDOW_SIZE = (1360, 760)
LEFT_PANEL_WIDTH = 430
OUTER_PAD_X = 20
PANEL_GAP = 12
RIGHT_PANEL_PAD_X = 24
RIGHT_PANEL_BORDER = 2
TABLE_SCROLLBAR_WIDTH = 22
AIR_WALL_EXTRA_WIDTH = 16
AIR_WALL_EXTRA_HEIGHT = 24
CELL_TEXT_PAD = 34
POINTS_TEXT_PAD = 70
NOTE_TEXT_PAD = 52
NAME_EXTRA_CHARS = "空空空"
ROOM_LIMIT_CHARS = "空空空空空空空空空空"
COLORS = {
    "app_bg": "#eef2f7",
    "panel": "#ffffff",
    "panel_alt": "#f8fafc",
    "line": "#d8dee8",
    "line_soft": "#e8edf5",
    "text": "#172033",
    "muted": "#667085",
    "soft_text": "#8a94a6",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "accent_active": "#1e40af",
    "accent_soft": "#eff6ff",
    "success": "#166534",
    "warning": "#9a3412",
    "danger": "#b42318",
}

COLUMN_LAYOUT = {
    "名称": {"weight": 1.0, "min": 185, "max": 260, "anchor": "w"},
    "入住时间": {"weight": 1.25, "min": 98, "max": 138, "anchor": "center"},
    "间夜": {"weight": 0.55, "min": 62, "max": 78, "anchor": "center"},
    "房型": {"weight": 0.85, "min": 105, "max": 170, "anchor": "w"},
    "总价": {"weight": 0.7, "min": 64, "max": 92, "anchor": "center"},
    "积分": {"weight": 1.35, "min": 135, "max": 210, "anchor": "center"},
    "备注": {"weight": 1.35, "min": 120, "max": 210, "anchor": "center"},
}

displayed_records = []
editing_index = None


def record_file_for_year(year):
    return BASE_DIR / f"{RECORD_FILE_PREFIX}_{year}.md"


def discover_record_years():
    discovered_years = {
        match.group(1)
        for path in BASE_DIR.glob(f"{RECORD_FILE_PREFIX}_*.md")
        if (match := re.fullmatch(rf"{RECORD_FILE_PREFIX}_(\d{{4}})\.md", path.name))
    }
    first_year = int(DEFAULT_YEAR)
    last_year = max(
        int(CURRENT_YEAR),
        *(int(year) for year in discovered_years) if discovered_years else [first_year],
    )
    return [str(year) for year in range(first_year, last_year + 1)]


def get_selected_year():
    return selected_year_var.get() if "selected_year_var" in globals() else DEFAULT_YEAR


def current_md_file():
    return record_file_for_year(get_selected_year())


def enable_high_dpi():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass


def init_md_file():
    md_file = current_md_file()
    legacy_file = BASE_DIR / f"{RECORD_FILE_PREFIX}.md"
    if not md_file.exists() and get_selected_year() == DEFAULT_YEAR and legacy_file.exists():
        legacy_file.replace(md_file)

    if not md_file.exists() or md_file.stat().st_size == 0:
        with md_file.open("w", encoding="utf-8", newline="") as f:
            f.write("# 酒店住宿记录\n\n")
            f.write("| " + " | ".join(HEADERS) + " |\n")
            f.write("| " + " | ".join([":---"] * len(HEADERS)) + " |\n")
        return

    migrate_md_columns()


def split_points_and_note(cells):
    points_index = HEADERS.index("积分")
    note_index = HEADERS.index("备注")
    if cells[points_index] and not cells[note_index]:
        match = re.match(r"^(.*?)(\s+[+-]\d+.*)$", cells[points_index])
        if match:
            cells[points_index] = match.group(1).strip()
            cells[note_index] = match.group(2).strip()
    return cells


def normalize_record_cells(cells):
    if len(cells) == len(OLD_HEADERS):
        cells = cells[:]
    elif len(cells) == len(AVG_HEADERS):
        cells = cells[:5] + cells[6:]
    return split_points_and_note(cells)


def migrate_md_columns():
    md_file = current_md_file()
    try:
        lines = md_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    changed = False
    migrated_lines = []
    table_header_seen = False
    separator_pending = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and not table_header_seen:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells in (OLD_HEADERS, HEADERS, AVG_HEADERS):
                migrated_lines.append("| " + " | ".join(HEADERS) + " |")
                table_header_seen = True
                separator_pending = True
                changed = changed or cells != HEADERS
                continue

        if separator_pending and stripped.startswith("|") and set(stripped.replace("|", "").replace(":", "").replace("-", "").strip()) == set():
            migrated_lines.append("| " + " | ".join([":---"] * len(HEADERS)) + " |")
            separator_pending = False
            changed = True
            continue

        if table_header_seen and stripped.startswith("|") and not stripped.startswith("| :---"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) in (len(HEADERS), len(OLD_HEADERS), len(AVG_HEADERS)):
                original_cells = cells.copy()
                updated_cells = normalize_record_cells(cells)
                migrated_lines.append("| " + " | ".join(updated_cells) + " |")
                changed = changed or updated_cells != original_cells
                continue

        migrated_lines.append(line)

    if changed:
        md_file.write_text("\n".join(migrated_lines) + "\n", encoding="utf-8")



def clean_markdown_cell(value):
    value = value.strip()
    value = re.sub(r"\s+", " ", value)
    return value.replace("|", "｜")


def normalize_nights(value):
    value = clean_markdown_cell(value)
    if not value:
        return value
    if value.isdigit():
        return f"{value}间夜"
    return value


def validate_record(record):
    if not record["名称"]:
        return "名称为必填项。"
    if not record["入住时间"]:
        return "入住时间为必填项。"
    if not DATE_RE.match(record["入住时间"]):
        return "入住时间格式应为 1.16-1.18 或 10.2-10.3。"
    if record["间夜"] and not NIGHTS_RE.match(record["间夜"]):
        return "间夜应填写为数字或类似 2间夜 的格式。"
    for field in ("总价", "积分"):
        if record[field] and record[field] != "/" and not re.search(r"\d", record[field]):
            return f"{field} 为空可以不填；如果填写，需要至少包含一个数字。"
    return None


def parse_markdown_records():
    init_md_file()
    records = []
    malformed_count = 0

    try:
        lines = current_md_file().read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"读取文件失败: {exc}") from exc

    for line in lines:
        stripped = line.strip()
        if not stripped or not stripped.startswith("|"):
            continue
        if stripped.startswith("| :---") or stripped == "| " + " | ".join(HEADERS) + " |":
            continue

        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells in (HEADERS, OLD_HEADERS, AVG_HEADERS):
            continue
        if len(cells) == len(OLD_HEADERS):
            cells = normalize_record_cells(cells)
        elif len(cells) == len(AVG_HEADERS):
            cells = normalize_record_cells(cells)
        if len(cells) != len(HEADERS):
            malformed_count += 1
            continue
        records.append(dict(zip(HEADERS, cells)))

    return records, malformed_count


def write_markdown_records(records):
    lines = [
        "# 酒店住宿记录",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join([":---"] * len(HEADERS)) + " |",
    ]
    for record in records:
        lines.append("| " + " | ".join(record.get(header, "") for header in HEADERS) + " |")
    current_md_file().write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_status(message, tone="neutral"):
    status_var.set(message)
    color = {
        "neutral": COLORS["muted"],
        "success": COLORS["success"],
        "warning": COLORS["warning"],
        "danger": COLORS["danger"],
    }.get(tone, COLORS["muted"])
    status_label.configure(fg=color)


def refresh_table():
    global displayed_records

    for item_id in record_table.get_children():
        record_table.delete(item_id)

    try:
        records, malformed_count = parse_markdown_records()
    except RuntimeError as exc:
        set_status(str(exc), "danger")
        messagebox.showerror("错误", str(exc))
        return []

    displayed_records = records
    update_column_layout_from_records(records)
    apply_window_air_wall(root)
    resize_table_columns()

    for index, record in enumerate(records):
        tag = "even" if index % 2 == 0 else "odd"
        values = [record[header] for header in HEADERS]
        record_table.insert("", tk.END, values=values, tags=(tag,))

    total_text = f"{len(records)} 条记录"
    if malformed_count:
        total_text += f"，{malformed_count} 行异常"
    summary_var.set(total_text)
    data_file_var.set(f"数据文件: {current_md_file().name}")

    if records:
        empty_state.place_forget()
    else:
        empty_state.place(relx=0.5, rely=0.52, anchor="center")

    if malformed_count:
        set_status(f"已显示 {len(records)} 条记录，跳过 {malformed_count} 行格式异常记录。", "warning")
    else:
        set_status(f"已显示 {len(records)} 条记录。")
    return records


def update_column_layout_from_records(records):
    table_font = tkfont.Font(root=root, family=FONT_FAMILY, size=TABLE_FONT[1])
    header_font = tkfont.Font(
        root=root,
        family=FONT_FAMILY,
        size=TABLE_HEADER_FONT[1],
        weight="bold",
    )
    room_limit_width = table_font.measure(ROOM_LIMIT_CHARS) + CELL_TEXT_PAD
    name_extra_width = table_font.measure(NAME_EXTRA_CHARS)

    for header_name in HEADERS:
        values = [header_name] + [record[header_name] for record in records]
        text_pad = CELL_TEXT_PAD
        if header_name == "积分":
            text_pad = POINTS_TEXT_PAD
        elif header_name == "备注":
            text_pad = NOTE_TEXT_PAD
        measured_width = max(
            header_font.measure(header_name),
            *(table_font.measure(value) for value in values),
        ) + text_pad
        spec = COLUMN_LAYOUT[header_name]
        spec["min"] = max(spec["min"], measured_width)

        if header_name == "名称":
            spec["max"] = max(spec["max"], measured_width + name_extra_width)
        elif header_name == "房型":
            spec["max"] = max(spec["max"], room_limit_width, measured_width)
        else:
            spec["max"] = max(spec["max"], measured_width)


def resize_table_columns(event=None):
    if event is not None and event.widget is not table_wrap:
        return

    available_width = table_wrap.winfo_width() - 22
    if available_width <= 120:
        return

    remaining_width = available_width
    remaining_columns = set(COLUMN_LAYOUT)
    widths = {header_name: spec["min"] for header_name, spec in COLUMN_LAYOUT.items()}
    remaining_width -= sum(widths.values())

    if remaining_width <= 0:
        for header_name, width in widths.items():
            record_table.column(header_name, width=width, minwidth=24, stretch=False)
        return

    while remaining_width > 0 and remaining_columns:
        total_weight = sum(COLUMN_LAYOUT[name]["weight"] for name in remaining_columns)
        used_width = 0
        capped_columns = set()

        for header_name in remaining_columns:
            spec = COLUMN_LAYOUT[header_name]
            extra = max(1, int(remaining_width * spec["weight"] / total_weight))
            candidate_width = widths[header_name] + extra
            max_width = spec["max"]
            if candidate_width >= max_width:
                extra = max_width - widths[header_name]
                capped_columns.add(header_name)
            widths[header_name] += max(0, extra)
            used_width += max(0, extra)

        if used_width == 0:
            break
        remaining_width -= used_width
        remaining_columns -= capped_columns

    for header_name, width in widths.items():
        record_table.column(header_name, width=width, minwidth=24, stretch=False)


def collect_record():
    points = clean_markdown_cell(entry_cost2.get()) or "/"
    return {
        "名称": clean_markdown_cell(entry_hotel.get()),
        "入住时间": clean_markdown_cell(entry_date.get()),
        "间夜": normalize_nights(entry_nights.get()),
        "房型": clean_markdown_cell(entry_room.get()),
        "总价": clean_markdown_cell(entry_cost1.get()),
        "积分": points,
        "备注": clean_markdown_cell(entry_note.get()),
    }


def fill_entries(record):
    for entry, header in zip(entries, HEADERS):
        entry.delete(0, tk.END)
        entry.insert(0, record.get(header, ""))


def clear_entries():
    for entry in entries:
        entry.delete(0, tk.END)


def enter_add_mode(clear_form=True):
    global editing_index

    editing_index = None
    form_title_var.set("新增住宿记录")
    form_subtitle_var.set("录入一次住宿，自动写入 Markdown 笔记。")
    submit_button.configure(text="添加记录到 Markdown")
    if clear_form:
        clear_entries()
    entry_hotel.focus_set()


def enter_edit_mode(record_index):
    global editing_index

    if record_index < 0 or record_index >= len(displayed_records):
        enter_add_mode()
        return

    editing_index = record_index
    form_title_var.set("编辑住宿记录")
    form_subtitle_var.set("正在修改选中的住宿记录，保存后会更新 Markdown。")
    submit_button.configure(text="保存修改到 Markdown")
    fill_entries(displayed_records[record_index])
    entry_hotel.focus_set()


def add_record():
    record = collect_record()
    validation_error = validate_record(record)
    if validation_error:
        set_status(validation_error, "danger")
        messagebox.showerror("错误", validation_error)
        return

    try:
        records, _ = parse_markdown_records()
    except RuntimeError as exc:
        set_status(str(exc), "danger")
        messagebox.showerror("错误", str(exc))
        return

    duplicate = any(
        old["名称"] == record["名称"] and old["入住时间"] == record["入住时间"]
        for old in records
    )
    if duplicate:
        should_continue = messagebox.askyesno(
            "发现重复记录",
            "已有相同名称和入住时间的记录，是否仍然继续保存？",
        )
        if not should_continue:
            set_status("已取消保存重复记录。", "warning")
            return

    row = "| " + " | ".join(record[header] for header in HEADERS) + " |\n"

    try:
        with current_md_file().open("a", encoding="utf-8", newline="") as f:
            f.write(row)
    except OSError as exc:
        message = f"写入文件失败: {exc}"
        set_status(message, "danger")
        messagebox.showerror("错误", message)
        return

    clear_entries()
    refresh_table()
    set_status(f"记录已保存到 {current_md_file().name}。", "success")
    entry_hotel.focus_set()


def edit_record():
    if editing_index is None:
        add_record()
        return

    record = collect_record()
    validation_error = validate_record(record)
    if validation_error:
        set_status(validation_error, "danger")
        messagebox.showerror("错误", validation_error)
        return

    try:
        records, _ = parse_markdown_records()
    except RuntimeError as exc:
        set_status(str(exc), "danger")
        messagebox.showerror("错误", str(exc))
        return

    if editing_index < 0 or editing_index >= len(records):
        message = "选中的记录已经不存在，请重新选择。"
        set_status(message, "warning")
        messagebox.showwarning("记录不存在", message)
        enter_add_mode()
        refresh_table()
        return

    duplicate = any(
        index != editing_index
        and old["名称"] == record["名称"]
        and old["入住时间"] == record["入住时间"]
        for index, old in enumerate(records)
    )
    if duplicate:
        should_continue = messagebox.askyesno(
            "发现重复记录",
            "已有其他相同名称和入住时间的记录，是否仍然继续保存？",
        )
        if not should_continue:
            set_status("已取消保存重复记录。", "warning")
            return

    records[editing_index] = record
    try:
        write_markdown_records(records)
    except OSError as exc:
        message = f"写入文件失败: {exc}"
        set_status(message, "danger")
        messagebox.showerror("错误", message)
        return

    saved_index = editing_index
    refresh_table()
    item_ids = record_table.get_children()
    if saved_index < len(item_ids):
        record_table.selection_set(item_ids[saved_index])
        record_table.focus(item_ids[saved_index])
        record_table.see(item_ids[saved_index])
        enter_edit_mode(saved_index)
    set_status(f"记录已更新到 {current_md_file().name}。", "success")


def submit_record():
    if editing_index is None:
        add_record()
    else:
        edit_record()


def handle_table_click(event):
    row_id = record_table.identify_row(event.y)
    region = record_table.identify("region", event.x, event.y)

    if row_id:
        record_table.selection_set(row_id)
        record_table.focus(row_id)
        enter_edit_mode(record_table.index(row_id))
    elif region == "nothing":
        record_table.selection_remove(record_table.selection())
        enter_add_mode()


def handle_year_change():
    record_table.selection_remove(record_table.selection())
    enter_add_mode()
    refresh_table()
    set_status(f"已切换到 {get_selected_year()} 年记录。")


def choose_year(year):
    selected_year_var.set(year)
    year_button.configure(text=year)
    handle_year_change()


def configure_styles(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=COLORS["app_bg"])
    root.option_add("*Font", BODY_FONT)

    style.configure(
        "App.TEntry",
        fieldbackground="#ffffff",
        foreground=COLORS["text"],
        bordercolor=COLORS["line"],
        lightcolor=COLORS["line"],
        darkcolor=COLORS["line"],
        padding=(10, 8),
    )
    style.map(
        "App.TEntry",
        bordercolor=[("focus", COLORS["accent"])],
        lightcolor=[("focus", COLORS["accent"])],
        darkcolor=[("focus", COLORS["accent"])],
    )
    style.configure(
        "Records.Treeview",
        background="#ffffff",
        fieldbackground="#ffffff",
        foreground=COLORS["text"],
        bordercolor=COLORS["line"],
        rowheight=38,
        font=TABLE_FONT,
    )
    style.configure(
        "Records.Treeview.Heading",
        background=COLORS["panel_alt"],
        foreground=COLORS["text"],
        bordercolor=COLORS["line"],
        relief="flat",
        font=TABLE_HEADER_FONT,
        padding=(8, 10),
    )
    style.map("Records.Treeview", background=[("selected", COLORS["accent"])])
    style.configure(
        "App.Vertical.TScrollbar",
        background=COLORS["panel_alt"],
        troughcolor="#ffffff",
        bordercolor=COLORS["line_soft"],
        arrowcolor=COLORS["muted"],
    )


def build_shell(root):
    root.title("酒店住宿数据录入器")
    root.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}")
    root.columnconfigure(0, weight=0)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=0)

    left_panel = tk.Frame(root, bg=COLORS["panel"], bd=0, highlightthickness=1, highlightbackground=COLORS["line"])
    left_panel.grid(row=0, column=0, sticky="ns", padx=(OUTER_PAD_X, PANEL_GAP), pady=20)
    left_panel.grid_propagate(False)
    left_panel.configure(width=LEFT_PANEL_WIDTH)

    right_panel = tk.Frame(root, bg=COLORS["panel"], bd=0, highlightthickness=1, highlightbackground=COLORS["line"])
    right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, OUTER_PAD_X), pady=20)
    right_panel.columnconfigure(0, weight=1)
    right_panel.rowconfigure(1, weight=1)

    return left_panel, right_panel


def add_section_label(parent, text, row):
    label = tk.Label(
        parent,
        text=text,
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=(FONT_FAMILY, 10, "bold"),
        anchor="w",
    )
    label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(18, 5))


def add_field(parent, row, label_text, required=False):
    label = tk.Label(
        parent,
        text=f"{label_text}{' *' if required else ''}",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=(FONT_FAMILY, 11, "bold" if required else "normal"),
        anchor="w",
    )
    label.grid(row=row, column=0, sticky="w", pady=6)

    entry = ttk.Entry(parent, style="App.TEntry", font=BODY_FONT)
    entry.grid(row=row, column=1, sticky="ew", pady=6, padx=(14, 0), ipady=2)
    return entry


def build_form_panel(parent):
    global form_title_var, form_subtitle_var, submit_button

    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(1, weight=1)

    header = tk.Frame(parent, bg=COLORS["panel"])
    header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
    header.columnconfigure(0, weight=1)

    form_title_var = tk.StringVar(value="新增住宿记录")
    title = tk.Label(
        header,
        textvariable=form_title_var,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=TITLE_FONT,
        anchor="w",
    )
    title.grid(row=0, column=0, sticky="ew")

    form_subtitle_var = tk.StringVar(value="录入一次住宿，自动写入 Markdown 笔记。")
    subtitle = tk.Label(
        header,
        textvariable=form_subtitle_var,
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=SMALL_FONT,
        anchor="w",
    )
    subtitle.grid(row=1, column=0, sticky="ew", pady=(6, 0))

    form = tk.Frame(parent, bg=COLORS["panel"])
    form.grid(row=1, column=0, sticky="nsew", padx=24, pady=(6, 20))
    form.columnconfigure(1, weight=1)

    row = 0
    add_section_label(form, "基础信息", row)
    row += 1
    hotel = add_field(form, row, "名称", required=True)
    row += 1
    date = add_field(form, row, "入住时间", required=True)
    row += 1
    nights = add_field(form, row, "间夜")
    row += 1
    room = add_field(form, row, "房型")
    row += 1

    add_section_label(form, "费用信息", row)
    row += 1
    cost1 = add_field(form, row, "总价")
    row += 1
    cost2 = add_field(form, row, "积分")
    row += 1

    add_section_label(form, "备注", row)
    row += 1
    note = add_field(form, row, "备注")
    row += 1

    hint = tk.Label(
        form,
        text="示例：入住时间 1.16-1.18，间夜 2间夜，备注 自住。",
        bg=COLORS["panel"],
        fg=COLORS["soft_text"],
        font=SMALL_FONT,
        anchor="w",
    )
    hint.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
    row += 1

    submit_button = tk.Button(
        form,
        text="添加记录到 Markdown",
        command=submit_record,
        bg=COLORS["accent"],
        activebackground=COLORS["accent_active"],
        fg="#ffffff",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        cursor="hand2",
        font=(FONT_FAMILY, 12, "bold"),
        padx=16,
        pady=11,
    )
    submit_button.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(18, 0))
    submit_button.bind("<Enter>", lambda _event: submit_button.configure(bg=COLORS["accent_hover"]))
    submit_button.bind("<Leave>", lambda _event: submit_button.configure(bg=COLORS["accent"]))

    return [hotel, date, nights, room, cost1, cost2, note]


def build_table_panel(parent):
    global record_table, empty_state, summary_var, table_wrap, selected_year_var, data_file_var, year_button

    header = tk.Frame(parent, bg=COLORS["panel"])
    header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 14))
    header.columnconfigure(0, weight=1)
    header.columnconfigure(1, weight=0)
    header.columnconfigure(2, weight=0)

    title = tk.Label(
        header,
        text="住宿记录",
        bg=COLORS["panel"],
        fg=COLORS["text"],
        font=TITLE_FONT,
        anchor="w",
    )
    title.grid(row=0, column=0, sticky="w")

    selected_year_var = tk.StringVar(value=DEFAULT_YEAR)
    year_frame = tk.Frame(header, bg=COLORS["panel"])
    year_frame.grid(row=0, column=1, sticky="e", padx=(16, 14))
    year_label = tk.Label(
        year_frame,
        text="年份:",
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=(FONT_FAMILY, 10, "bold"),
    )
    year_label.pack(side=tk.LEFT, padx=(0, 4))
    year_button = tk.Menubutton(
        year_frame,
        text=selected_year_var.get(),
        bg=COLORS["accent_soft"],
        activebackground="#dbeafe",
        fg=COLORS["accent"],
        activeforeground=COLORS["accent"],
        relief="flat",
        bd=0,
        cursor="hand2",
        font=(FONT_FAMILY, 10, "bold"),
        padx=12,
        pady=5,
        direction="below",
    )
    year_menu = tk.Menu(
        year_button,
        tearoff=0,
        bg="#ffffff",
        fg=COLORS["text"],
        activebackground=COLORS["accent_soft"],
        activeforeground=COLORS["accent"],
        font=(FONT_FAMILY, 10),
        relief="flat",
        bd=1,
    )
    for year in discover_record_years():
        year_menu.add_command(label=year, command=lambda selected=year: choose_year(selected))
    year_button.configure(menu=year_menu)
    year_button.pack(side=tk.LEFT)

    summary_var = tk.StringVar(value="0 条记录")
    summary = tk.Label(
        header,
        textvariable=summary_var,
        bg=COLORS["accent_soft"],
        fg=COLORS["accent"],
        font=(FONT_FAMILY, 11, "bold"),
        padx=12,
        pady=5,
    )
    summary.grid(row=0, column=2, sticky="e")

    data_file_var = tk.StringVar(value=f"数据文件: {current_md_file().name}")
    subtitle = tk.Label(
        header,
        textvariable=data_file_var,
        bg=COLORS["panel"],
        fg=COLORS["muted"],
        font=SMALL_FONT,
        anchor="w",
    )
    subtitle.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))

    table_wrap = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
    table_wrap.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
    table_wrap.columnconfigure(0, weight=1)
    table_wrap.rowconfigure(0, weight=1)

    record_table = ttk.Treeview(table_wrap, columns=HEADERS, show="headings", style="Records.Treeview")
    scrollbar = ttk.Scrollbar(
        table_wrap,
        orient=tk.VERTICAL,
        command=record_table.yview,
        style="App.Vertical.TScrollbar",
    )
    record_table.configure(yscrollcommand=scrollbar.set)

    for header_name in HEADERS:
        record_table.heading(header_name, text=header_name)
        record_table.column(
            header_name,
            width=COLUMN_LAYOUT[header_name]["min"],
            minwidth=24,
            anchor=COLUMN_LAYOUT[header_name]["anchor"],
            stretch=False,
        )

    record_table.tag_configure("even", background="#ffffff")
    record_table.tag_configure("odd", background=COLORS["panel_alt"])
    record_table.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    table_wrap.bind("<Configure>", resize_table_columns)
    record_table.bind("<ButtonRelease-1>", handle_table_click)

    empty_state = tk.Label(
        table_wrap,
        text="暂无记录\n在左侧添加第一条住宿记录后，这里会自动刷新。",
        bg="#ffffff",
        fg=COLORS["soft_text"],
        font=BODY_FONT,
        justify="center",
    )


def calculate_window_min_size(root):
    root.update_idletasks()

    table_min_width = sum(spec["min"] for spec in COLUMN_LAYOUT.values())
    right_min_width = (
        table_min_width
        + TABLE_SCROLLBAR_WIDTH
        + RIGHT_PANEL_PAD_X * 2
        + RIGHT_PANEL_BORDER
    )
    min_width = (
        LEFT_PANEL_WIDTH
        + right_min_width
        + OUTER_PAD_X * 2
        + PANEL_GAP
        + AIR_WALL_EXTRA_WIDTH
    )

    content_height = max(left_panel.winfo_reqheight(), right_panel.winfo_reqheight())
    status_height = status_label.winfo_reqheight()
    min_height = content_height + status_height + 20 * 2 + 14 + AIR_WALL_EXTRA_HEIGHT

    return int(min_width), int(min_height)


def apply_window_air_wall(root):
    min_width, min_height = calculate_window_min_size(root)
    root.minsize(min_width, min_height)

    current_width = max(root.winfo_width(), DEFAULT_WINDOW_SIZE[0], min_width)
    current_height = max(root.winfo_height(), DEFAULT_WINDOW_SIZE[1], min_height)
    root.geometry(f"{current_width}x{current_height}")
    root.update_idletasks()


def build_status_bar(root):
    global status_var, status_label

    status_frame = tk.Frame(root, bg=COLORS["app_bg"])
    status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 14))
    status_frame.columnconfigure(0, weight=1)

    status_var = tk.StringVar(value="")
    status_label = tk.Label(
        status_frame,
        textvariable=status_var,
        bg=COLORS["app_bg"],
        fg=COLORS["muted"],
        font=SMALL_FONT,
        anchor="w",
    )
    status_label.grid(row=0, column=0, sticky="ew")


enable_high_dpi()

root = tk.Tk()
configure_styles(root)
left_panel, right_panel = build_shell(root)
build_status_bar(root)
entries = build_form_panel(left_panel)
entry_hotel, entry_date, entry_nights, entry_room, entry_cost1, entry_cost2, entry_note = entries
build_table_panel(right_panel)

apply_window_air_wall(root)
refresh_table()
entry_hotel.focus_set()

root.mainloop()
