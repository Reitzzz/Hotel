import ctypes
import copy
import re
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

try:
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import messagebox, ttk
except ModuleNotFoundError:
    tk = None
    tkfont = None
    messagebox = None
    ttk = None


BASE_DIR = Path(__file__).resolve().parent
RECORD_FILE_PREFIX = "hotel_stay_records"
DEFAULT_YEAR = "2025"
CURRENT_YEAR = str(date.today().year)

HEADERS = ["名称", "入住时间", "间夜", "房型", "总价", "积分", "备注"]
OLD_HEADERS = ["酒店名称", "日期", "间夜", "房型", "费用1", "费用2 / 报销", "备注"]
AVG_HEADERS = ["名称", "入住时间", "间夜", "房型", "总价", "均价", "积分", "备注"]
DATE_PART_RE = re.compile(r"^\d{1,2}\.\d{1,2}$")
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

BASE_COLUMN_LAYOUT = {
    "名称": {"weight": 1.0, "min": 185, "max": 260, "anchor": "w"},
    "入住时间": {"weight": 1.25, "min": 98, "max": 138, "anchor": "center"},
    "间夜": {"weight": 0.55, "min": 62, "max": 78, "anchor": "center"},
    "房型": {"weight": 0.85, "min": 105, "max": 170, "anchor": "center"},
    "总价": {"weight": 0.7, "min": 64, "max": 92, "anchor": "center"},
    "积分": {"weight": 1.35, "min": 135, "max": 210, "anchor": "center"},
    "备注": {"weight": 1.35, "min": 120, "max": 210, "anchor": "center"},
}


def record_file_for_year(year):
    return BASE_DIR / f"{RECORD_FILE_PREFIX}_{year}.md"


def discover_record_years():
    discovered_years = {
        match.group(1)
        for path in BASE_DIR.glob(f"{RECORD_FILE_PREFIX}_*.md")
        if (match := re.fullmatch(rf"{RECORD_FILE_PREFIX}_(\d{{4}})\.md", path.name))
    }
    first_year = int(DEFAULT_YEAR)
    candidate_years = {int(CURRENT_YEAR), first_year}
    candidate_years.update(int(year) for year in discovered_years)
    last_year = max(candidate_years)
    return [str(year) for year in range(first_year, last_year + 1)]


def current_md_file(year=DEFAULT_YEAR):
    return record_file_for_year(year)


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


def init_md_file(year=DEFAULT_YEAR):
    md_file = current_md_file(year)
    legacy_file = BASE_DIR / f"{RECORD_FILE_PREFIX}.md"
    if not md_file.exists() and year == DEFAULT_YEAR and legacy_file.exists():
        legacy_file.replace(md_file)

    if not md_file.exists() or md_file.stat().st_size == 0:
        with md_file.open("w", encoding="utf-8", newline="\n") as f:
            f.write("# 酒店住宿记录\n\n")
            f.write("| " + " | ".join(HEADERS) + " |\n")
            f.write("| " + " | ".join([":---"] * len(HEADERS)) + " |\n")
        return

    migrate_md_columns(year)


def split_points_and_note(cells):
    points_index = HEADERS.index("积分")
    note_index = HEADERS.index("备注")
    if cells[points_index] and not cells[note_index]:
        match = re.match(r"^(.*?)(\s+[+-]\d+.*)$", cells[points_index])
        if match:
            cells[points_index] = match.group(1).strip()
            cells[note_index] = match.group(2).strip()
    return cells


def normalize_record_cells(cells, source_headers=None):
    if source_headers == OLD_HEADERS:
        cells = cells[:]
    elif source_headers == AVG_HEADERS or len(cells) == len(AVG_HEADERS):
        cells = cells[:5] + cells[6:]
    return split_points_and_note(cells)


def migrate_md_columns(year=DEFAULT_YEAR):
    md_file = current_md_file(year)
    try:
        lines = md_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return

    changed = False
    migrated_lines = []
    table_header_seen = False
    source_headers = HEADERS
    separator_pending = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and not table_header_seen:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells in (OLD_HEADERS, HEADERS, AVG_HEADERS):
                migrated_lines.append("| " + " | ".join(HEADERS) + " |")
                table_header_seen = True
                source_headers = cells
                separator_pending = True
                changed = changed or cells != HEADERS
                continue

        if separator_pending and stripped.startswith("|") and set(stripped.replace("|", "").replace(":", "").replace("-", "").strip()) == set():
            separator_line = "| " + " | ".join([":---"] * len(HEADERS)) + " |"
            migrated_lines.append(separator_line)
            separator_pending = False
            changed = changed or line != separator_line
            continue

        if table_header_seen and stripped.startswith("|") and not stripped.startswith("| :---"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) in (len(HEADERS), len(OLD_HEADERS), len(AVG_HEADERS)):
                original_cells = cells.copy()
                updated_cells = normalize_record_cells(cells, source_headers)
                migrated_lines.append("| " + " | ".join(updated_cells) + " |")
                changed = changed or updated_cells != original_cells
                continue

        migrated_lines.append(line)

    if changed:
        md_file.write_text("\n".join(migrated_lines) + "\n", encoding="utf-8", newline="\n")



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


def parse_month_day(value):
    if not DATE_PART_RE.match(value):
        return None
    month, day = (int(part) for part in value.split(".", 1))
    if not is_valid_month_day(month, day):
        return None
    return month, day


def parse_stay_date_range(value):
    match = DATE_RE.match(value)
    if not match:
        return None

    start_text, end_text = value.split("-", 1)
    start_month, start_day = (int(part) for part in start_text.split(".", 1))
    end_month, end_day = (int(part) for part in end_text.split(".", 1))
    return start_month, start_day, end_month, end_day


def is_valid_month_day(month, day):
    if month < 1 or month > 12:
        return False
    return 1 <= day <= monthrange(2000, month)[1]


def build_stay_date_range(checkin, checkout):
    checkin = clean_markdown_cell(checkin)
    checkout = clean_markdown_cell(checkout)
    if not checkin:
        return None, "入住时间为必填项。"
    if not checkout:
        return None, "离店时间为必填项。"
    if parse_month_day(checkin) is None:
        return None, "入住时间格式应为 1.16 或 10.2。"
    if parse_month_day(checkout) is None:
        return None, "离店时间格式应为 1.18 或 10.3。"

    stay_range = f"{checkin}-{checkout}"
    date_error = validate_stay_date_range(stay_range)
    if date_error:
        return None, date_error
    return stay_range, None


def calculate_nights(stay_range):
    parsed = parse_stay_date_range(stay_range)
    if parsed is None:
        return ""
    start_month, start_day, end_month, end_day = parsed
    start_ordinal = date(2000, start_month, start_day).toordinal()
    end_year = 2001 if end_month < start_month else 2000
    end_ordinal = date(end_year, end_month, end_day).toordinal()
    return f"{end_ordinal - start_ordinal}间夜"


def split_stay_date_range(stay_range):
    if not DATE_RE.match(stay_range):
        return stay_range, ""
    return stay_range.split("-", 1)


def validate_stay_date_range(value):
    parsed = parse_stay_date_range(value)
    if parsed is None:
        return "入住时间格式应为 1.16-1.18、8.29-9.2 或 12.30-1.2。"

    start_month, start_day, end_month, end_day = parsed
    if not is_valid_month_day(start_month, start_day) or not is_valid_month_day(end_month, end_day):
        return "入住时间包含无效的月份或日期。"

    start_ordinal = date(2000, start_month, start_day).toordinal()
    end_year = 2001 if end_month < start_month else 2000
    end_ordinal = date(end_year, end_month, end_day).toordinal()
    if end_ordinal <= start_ordinal:
        return "退房日期应晚于入住日期。"

    return None


def validate_record(record):
    if not record["名称"]:
        return "名称为必填项。"
    if not record["入住时间"]:
        return "入住时间为必填项。"
    date_error = validate_stay_date_range(record["入住时间"])
    if date_error:
        return date_error
    if record["间夜"] and not NIGHTS_RE.match(record["间夜"]):
        return "间夜应填写为数字或类似 2间夜 的格式。"
    for field in ("总价", "积分"):
        if record[field] and record[field] != "/" and not re.search(r"\d", record[field]):
            return f"{field} 为空可以不填；如果填写，需要至少包含一个数字。"
    return None


def parse_markdown_records(year=DEFAULT_YEAR):
    init_md_file(year)
    records = []
    malformed_count = 0
    source_headers = HEADERS

    try:
        lines = current_md_file(year).read_text(encoding="utf-8").splitlines()
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
            source_headers = cells
            continue
        if len(cells) == len(OLD_HEADERS):
            cells = normalize_record_cells(cells, source_headers)
        elif len(cells) == len(AVG_HEADERS):
            cells = normalize_record_cells(cells, source_headers)
        if len(cells) != len(HEADERS):
            malformed_count += 1
            continue
        records.append(dict(zip(HEADERS, cells)))

    return records, malformed_count


def write_markdown_records(records, year=DEFAULT_YEAR):
    lines = [
        "# 酒店住宿记录",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join([":---"] * len(HEADERS)) + " |",
    ]
    for record in records:
        lines.append("| " + " | ".join(record.get(header, "") for header in HEADERS) + " |")
    current_md_file(year).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def has_duplicate_record(records, record, exclude_index=None):
    return any(
        (exclude_index is None or index != exclude_index)
        and old["名称"] == record["名称"]
        and old["入住时间"] == record["入住时间"]
        for index, old in enumerate(records)
    )


class HotelManagerApp:
    def __init__(self, root):
        self.root = root
        self.column_layout = copy.deepcopy(BASE_COLUMN_LAYOUT)
        self.displayed_records = []
        self.editing_index = None
        self.entries = {}

        self.configure_styles()
        self.left_panel, self.right_panel = self.build_shell()
        self.build_status_bar()
        self.build_form_panel(self.left_panel)
        self.build_table_panel(self.right_panel)

        self.apply_window_air_wall()
        self.refresh_table()
        self.entries["名称"].focus_set()

    def selected_year(self):
        return self.selected_year_var.get()

    def set_status(self, message, tone="neutral"):
        self.status_var.set(message)
        color = {
            "neutral": COLORS["muted"],
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
        }.get(tone, COLORS["muted"])
        self.status_label.configure(fg=color)

    def report_runtime_error(self, exc):
        self.set_status(str(exc), "danger")
        messagebox.showerror("错误", str(exc))

    def load_records(self):
        try:
            return parse_markdown_records(self.selected_year())
        except RuntimeError as exc:
            self.report_runtime_error(exc)
            return None

    def save_records(self, records):
        try:
            write_markdown_records(records, self.selected_year())
        except OSError as exc:
            message = f"写入文件失败: {exc}"
            self.set_status(message, "danger")
            messagebox.showerror("错误", message)
            return False
        return True

    def refresh_table(self):
        for item_id in self.record_table.get_children():
            self.record_table.delete(item_id)

        loaded = self.load_records()
        if loaded is None:
            return []
        records, malformed_count = loaded

        self.displayed_records = records
        self.update_column_layout_from_records(records)
        self.apply_window_air_wall()
        self.resize_table_columns()

        for index, record in enumerate(records):
            tag = "even" if index % 2 == 0 else "odd"
            values = [record[header] for header in HEADERS]
            self.record_table.insert("", tk.END, values=values, tags=(tag,))

        total_text = f"{len(records)} 条记录"
        if malformed_count:
            total_text += f"，{malformed_count} 行异常"
        self.summary_var.set(total_text)
        self.data_file_var.set(f"数据文件: {current_md_file(self.selected_year()).name}")

        if records:
            self.empty_state.place_forget()
        else:
            self.empty_state.place(relx=0.5, rely=0.52, anchor="center")

        if malformed_count:
            self.set_status(f"已显示 {len(records)} 条记录，跳过 {malformed_count} 行格式异常记录。", "warning")
        else:
            self.set_status(f"已显示 {len(records)} 条记录。")
        return records

    def update_column_layout_from_records(self, records):
        layout = copy.deepcopy(BASE_COLUMN_LAYOUT)
        table_font = tkfont.Font(root=self.root, family=FONT_FAMILY, size=TABLE_FONT[1])
        header_font = tkfont.Font(
            root=self.root,
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
            spec = layout[header_name]
            spec["min"] = max(spec["min"], measured_width)

            if header_name == "名称":
                spec["max"] = max(spec["max"], measured_width + name_extra_width)
            elif header_name == "房型":
                spec["max"] = max(spec["max"], room_limit_width, measured_width)
            else:
                spec["max"] = max(spec["max"], measured_width)

        self.column_layout = layout

    def resize_table_columns(self, event=None):
        if event is not None and event.widget is not self.table_wrap:
            return

        available_width = self.table_wrap.winfo_width() - TABLE_SCROLLBAR_WIDTH
        if available_width <= 120:
            return

        remaining_width = available_width
        remaining_columns = set(self.column_layout)
        widths = {header_name: spec["min"] for header_name, spec in self.column_layout.items()}
        remaining_width -= sum(widths.values())

        if remaining_width <= 0:
            for header_name, width in widths.items():
                self.record_table.column(header_name, width=width, minwidth=24, stretch=False)
            return

        while remaining_width > 0 and remaining_columns:
            total_weight = sum(self.column_layout[name]["weight"] for name in remaining_columns)
            used_width = 0
            capped_columns = set()

            for header_name in remaining_columns:
                spec = self.column_layout[header_name]
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
            self.record_table.column(header_name, width=width, minwidth=24, stretch=False)

    def collect_record(self):
        points = clean_markdown_cell(self.entries["积分"].get()) or "/"
        stay_range, date_error = build_stay_date_range(
            self.entries["入住时间"].get(),
            self.entries["离店时间"].get(),
        )
        if date_error:
            return None, date_error

        return {
            "名称": clean_markdown_cell(self.entries["名称"].get()),
            "入住时间": stay_range,
            "间夜": calculate_nights(stay_range),
            "房型": clean_markdown_cell(self.entries["房型"].get()),
            "总价": clean_markdown_cell(self.entries["总价"].get()),
            "积分": points,
            "备注": clean_markdown_cell(self.entries["备注"].get()),
        }, None

    def fill_entries(self, record):
        for header, entry in self.entries.items():
            entry.delete(0, tk.END)
            if header == "入住时间":
                value, _ = split_stay_date_range(record.get("入住时间", ""))
            elif header == "离店时间":
                _, value = split_stay_date_range(record.get("入住时间", ""))
            else:
                value = record.get(header, "")
            entry.insert(0, value)

    def clear_entries(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def enter_add_mode(self, clear_form=True):
        self.editing_index = None
        self.form_title_var.set("新增住宿记录")
        self.form_subtitle_var.set("录入一次住宿，自动写入 Markdown 笔记。")
        self.submit_button.configure(text="添加记录到 Markdown")
        self.delete_button.configure(state=tk.DISABLED)
        if clear_form:
            self.clear_entries()
        self.entries["名称"].focus_set()

    def enter_edit_mode(self, record_index):
        if record_index < 0 or record_index >= len(self.displayed_records):
            self.enter_add_mode()
            return

        self.editing_index = record_index
        self.form_title_var.set("编辑住宿记录")
        self.form_subtitle_var.set("修改选中记录，保存后更新 Markdown。")
        self.submit_button.configure(text="保存修改到 Markdown")
        self.delete_button.configure(state=tk.NORMAL)
        self.fill_entries(self.displayed_records[record_index])
        self.entries["名称"].focus_set()

    def confirm_duplicate(self, records, record, exclude_index=None):
        if not has_duplicate_record(records, record, exclude_index):
            return True
        message = (
            "已有其他相同名称和入住时间的记录，是否仍然继续保存？"
            if exclude_index is not None
            else "已有相同名称和入住时间的记录，是否仍然继续保存？"
        )
        should_continue = messagebox.askyesno("发现重复记录", message)
        if not should_continue:
            self.set_status("已取消保存重复记录。", "warning")
        return should_continue

    def add_record(self):
        record, form_error = self.collect_record()
        validation_error = form_error or validate_record(record)
        if validation_error:
            self.set_status(validation_error, "danger")
            messagebox.showerror("错误", validation_error)
            return

        loaded = self.load_records()
        if loaded is None:
            return
        records, _ = loaded
        if not self.confirm_duplicate(records, record):
            return

        records.append(record)
        if not self.save_records(records):
            return

        self.clear_entries()
        self.refresh_table()
        self.set_status(f"记录已保存到 {current_md_file(self.selected_year()).name}。", "success")
        self.entries["名称"].focus_set()

    def edit_record(self):
        if self.editing_index is None:
            self.add_record()
            return

        record, form_error = self.collect_record()
        validation_error = form_error or validate_record(record)
        if validation_error:
            self.set_status(validation_error, "danger")
            messagebox.showerror("错误", validation_error)
            return

        loaded = self.load_records()
        if loaded is None:
            return
        records, _ = loaded

        if self.editing_index < 0 or self.editing_index >= len(records):
            message = "选中的记录已经不存在，请重新选择。"
            self.set_status(message, "warning")
            messagebox.showwarning("记录不存在", message)
            self.enter_add_mode()
            self.refresh_table()
            return

        if not self.confirm_duplicate(records, record, self.editing_index):
            return

        records[self.editing_index] = record
        if not self.save_records(records):
            return

        saved_index = self.editing_index
        self.refresh_table()
        item_ids = self.record_table.get_children()
        if saved_index < len(item_ids):
            self.record_table.selection_set(item_ids[saved_index])
            self.record_table.focus(item_ids[saved_index])
            self.record_table.see(item_ids[saved_index])
            self.enter_edit_mode(saved_index)
        self.set_status(f"记录已更新到 {current_md_file(self.selected_year()).name}。", "success")

    def delete_record(self):
        if self.editing_index is None:
            self.set_status("请先选择要删除的记录。", "warning")
            return

        loaded = self.load_records()
        if loaded is None:
            return
        records, _ = loaded
        if self.editing_index < 0 or self.editing_index >= len(records):
            message = "选中的记录已经不存在，请重新选择。"
            self.set_status(message, "warning")
            messagebox.showwarning("记录不存在", message)
            self.enter_add_mode()
            self.refresh_table()
            return

        record = records[self.editing_index]
        message = f"确定删除“{record['名称']} / {record['入住时间']}”这条记录吗？"
        if not messagebox.askyesno("删除记录", message):
            self.set_status("已取消删除。", "warning")
            return

        del records[self.editing_index]
        if not self.save_records(records):
            return

        self.enter_add_mode()
        self.refresh_table()
        self.set_status(f"记录已从 {current_md_file(self.selected_year()).name} 删除。", "success")

    def submit_record(self):
        if self.editing_index is None:
            self.add_record()
        else:
            self.edit_record()

    def handle_table_click(self, event):
        row_id = self.record_table.identify_row(event.y)
        region = self.record_table.identify("region", event.x, event.y)

        if row_id:
            self.record_table.selection_set(row_id)
            self.record_table.focus(row_id)
            self.enter_edit_mode(self.record_table.index(row_id))
        elif region == "nothing":
            self.record_table.selection_remove(self.record_table.selection())
            self.enter_add_mode()

    def handle_year_change(self):
        self.record_table.selection_remove(self.record_table.selection())
        self.enter_add_mode()
        self.refresh_table()
        self.set_status(f"已切换到 {self.selected_year()} 年记录。")

    def choose_year(self, year):
        self.selected_year_var.set(year)
        self.year_button.configure(text=year)
        self.handle_year_change()

    def configure_styles(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.root.configure(bg=COLORS["app_bg"])
        self.root.option_add("*Font", BODY_FONT)

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

    def build_shell(self):
        self.root.title("酒店住宿数据录入器")
        self.root.geometry(f"{DEFAULT_WINDOW_SIZE[0]}x{DEFAULT_WINDOW_SIZE[1]}")
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        left_panel = tk.Frame(self.root, bg=COLORS["panel"], bd=0, highlightthickness=1, highlightbackground=COLORS["line"])
        left_panel.grid(row=0, column=0, sticky="ns", padx=(OUTER_PAD_X, PANEL_GAP), pady=20)
        left_panel.grid_propagate(False)
        left_panel.configure(width=LEFT_PANEL_WIDTH)

        right_panel = tk.Frame(self.root, bg=COLORS["panel"], bd=0, highlightthickness=1, highlightbackground=COLORS["line"])
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, OUTER_PAD_X), pady=20)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)

        return left_panel, right_panel

    def add_section_label(self, parent, text, row):
        label = tk.Label(
            parent,
            text=text,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 10, "bold"),
            anchor="w",
        )
        label.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(18, 5))

    def add_field(self, parent, row, label_text, required=False):
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
        self.entries[label_text] = entry
        return entry

    def build_form_panel(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        header = tk.Frame(parent, bg=COLORS["panel"])
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 8))
        header.columnconfigure(0, weight=1)

        self.form_title_var = tk.StringVar(value="新增住宿记录")
        title = tk.Label(
            header,
            textvariable=self.form_title_var,
            bg=COLORS["panel"],
            fg=COLORS["text"],
            font=TITLE_FONT,
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew")

        self.form_subtitle_var = tk.StringVar(value="录入一次住宿，自动写入 Markdown 笔记。")
        subtitle = tk.Label(
            header,
            textvariable=self.form_subtitle_var,
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
        self.add_section_label(form, "基础信息", row)
        row += 1
        self.add_field(form, row, "名称", required=True)
        row += 1
        self.add_field(form, row, "入住时间", required=True)
        row += 1
        self.add_field(form, row, "离店时间", required=True)
        row += 1
        self.add_field(form, row, "房型")
        row += 1

        self.add_section_label(form, "费用信息", row)
        row += 1
        self.add_field(form, row, "总价")
        row += 1
        self.add_field(form, row, "积分")
        row += 1

        self.add_section_label(form, "备注", row)
        row += 1
        self.add_field(form, row, "备注")
        row += 1

        hint = tk.Label(
            form,
            text="示例：入住时间 1.16，离店时间 1.18，备注 自住。",
            bg=COLORS["panel"],
            fg=COLORS["soft_text"],
            font=SMALL_FONT,
            anchor="w",
        )
        hint.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        row += 1

        actions = tk.Frame(form, bg=COLORS["panel"])
        actions.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=0)

        self.submit_button = tk.Button(
            actions,
            text="添加记录到 Markdown",
            command=self.submit_record,
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
        self.submit_button.grid(row=0, column=0, sticky="ew")
        self.submit_button.bind("<Enter>", lambda _event: self.submit_button.configure(bg=COLORS["accent_hover"]))
        self.submit_button.bind("<Leave>", lambda _event: self.submit_button.configure(bg=COLORS["accent"]))

        self.delete_button = tk.Button(
            actions,
            text="删除",
            command=self.delete_record,
            bg="#fee2e2",
            activebackground="#fecaca",
            fg=COLORS["danger"],
            activeforeground=COLORS["danger"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=(FONT_FAMILY, 12, "bold"),
            padx=16,
            pady=11,
            state=tk.DISABLED,
        )
        self.delete_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

    def build_table_panel(self, parent):
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

        self.selected_year_var = tk.StringVar(value=DEFAULT_YEAR)
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
        self.year_button = tk.Menubutton(
            year_frame,
            text=self.selected_year_var.get(),
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
            self.year_button,
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
            year_menu.add_command(label=year, command=lambda selected=year: self.choose_year(selected))
        self.year_button.configure(menu=year_menu)
        self.year_button.pack(side=tk.LEFT)

        self.summary_var = tk.StringVar(value="0 条记录")
        summary = tk.Label(
            header,
            textvariable=self.summary_var,
            bg=COLORS["accent_soft"],
            fg=COLORS["accent"],
            font=(FONT_FAMILY, 11, "bold"),
            padx=12,
            pady=5,
        )
        summary.grid(row=0, column=2, sticky="e")

        self.data_file_var = tk.StringVar(value=f"数据文件: {current_md_file(self.selected_year()).name}")
        subtitle = tk.Label(
            header,
            textvariable=self.data_file_var,
            bg=COLORS["panel"],
            fg=COLORS["muted"],
            font=SMALL_FONT,
            anchor="w",
        )
        subtitle.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        self.table_wrap = tk.Frame(parent, bg=COLORS["panel"], highlightthickness=1, highlightbackground=COLORS["line"])
        self.table_wrap.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.table_wrap.columnconfigure(0, weight=1)
        self.table_wrap.rowconfigure(0, weight=1)

        self.record_table = ttk.Treeview(self.table_wrap, columns=HEADERS, show="headings", style="Records.Treeview")
        scrollbar = ttk.Scrollbar(
            self.table_wrap,
            orient=tk.VERTICAL,
            command=self.record_table.yview,
            style="App.Vertical.TScrollbar",
        )
        self.record_table.configure(yscrollcommand=scrollbar.set)

        for header_name in HEADERS:
            self.record_table.heading(header_name, text=header_name)
            self.record_table.column(
                header_name,
                width=self.column_layout[header_name]["min"],
                minwidth=24,
                anchor=self.column_layout[header_name]["anchor"],
                stretch=False,
            )

        self.record_table.tag_configure("even", background="#ffffff")
        self.record_table.tag_configure("odd", background=COLORS["panel_alt"])
        self.record_table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.table_wrap.bind("<Configure>", self.resize_table_columns)
        self.record_table.bind("<ButtonRelease-1>", self.handle_table_click)

        self.empty_state = tk.Label(
            self.table_wrap,
            text="暂无记录\n在左侧添加第一条住宿记录后，这里会自动刷新。",
            bg="#ffffff",
            fg=COLORS["soft_text"],
            font=BODY_FONT,
            justify="center",
        )

    def calculate_window_min_size(self):
        self.root.update_idletasks()

        table_min_width = sum(spec["min"] for spec in self.column_layout.values())
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

        content_height = max(self.left_panel.winfo_reqheight(), self.right_panel.winfo_reqheight())
        status_height = self.status_label.winfo_reqheight()
        min_height = content_height + status_height + 20 * 2 + 14 + AIR_WALL_EXTRA_HEIGHT

        return int(min_width), int(min_height)

    def apply_window_air_wall(self):
        min_width, min_height = self.calculate_window_min_size()
        self.root.minsize(min_width, min_height)

        current_width = max(self.root.winfo_width(), DEFAULT_WINDOW_SIZE[0], min_width)
        current_height = max(self.root.winfo_height(), DEFAULT_WINDOW_SIZE[1], min_height)
        self.root.geometry(f"{current_width}x{current_height}")
        self.root.update_idletasks()

    def build_status_bar(self):
        status_frame = tk.Frame(self.root, bg=COLORS["app_bg"])
        status_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 14))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg=COLORS["app_bg"],
            fg=COLORS["muted"],
            font=SMALL_FONT,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew")


def main():
    if tk is None:
        raise RuntimeError("当前 Python 环境缺少 tkinter，无法启动图形界面。")
    enable_high_dpi()
    root = tk.Tk()
    app = HotelManagerApp(root)
    root.mainloop()
    return app


if __name__ == "__main__":
    main()
