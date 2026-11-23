"""真实 Tk 控件回归；所有数据写入系统临时目录。"""

import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hotel_manager as hotel


class TableNoteTests(unittest.TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory(prefix="hotel-note-tests-")
        self.addCleanup(self.storage.cleanup)
        directory = Path(self.storage.name)
        for name, value in (
            ("BASE_DIR", directory / "data"),
            ("AUTO_BACKUP_DIR", directory / "autosave"),
            ("LEGACY_DATA_DIRS", ()),
        ):
            context = patch.object(hotel, name, value)
            context.start()
            self.addCleanup(context.stop)
        self.note = "春节涨价，平常价格为184元；" * 20 + "尾部信息必须保留。"
        record = dict.fromkeys(hotel.HEADERS, "")
        record.update({"名称": "长备注测试酒店", "入住时间": "2.21-2.22",
                       "间夜": "1间夜", "房型": "家庭房", "总价": "523",
                       "积分": "1357", "版本": "3.5", "备注": self.note})
        self.records = [record, dict(record, 名称="无备注酒店", 入住时间="3.1-3.2", 备注="")]
        hotel.write_markdown_records(self.records)
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.app = hotel.HotelManagerApp(self.root)
        self.root.update()

    def resize(self, width):
        self.root.minsize(1, 1)
        self.root.geometry(f"{width}x900+0+0")
        self.root.update()

    def select(self, index):
        item = self.app.record_table.get_children()[index]
        self.app.record_table.selection_set(item)
        self.app.record_table.focus(item)
        self.root.update()
        return item

    def test_columns_remain_inside_table_with_long_note(self):
        for width in (1360, 1600, 1920):
            with self.subTest(width=width):
                self.resize(width)
                total = sum(self.app.record_table.column(name, "width") for name in hotel.HEADERS)
                self.assertLessEqual(total, self.app.record_table.winfo_width() - 4)
                self.assertEqual(self.app.record_table.xview(), (0.0, 1.0))

    def test_summary_changes_with_width_without_changing_original(self):
        self.resize(1360)
        item = self.select(0)
        narrow = self.app.record_table.set(item, "备注")
        self.assertTrue(narrow.endswith("…"))
        self.assertTrue(self.note.startswith(narrow[:-1]))
        self.assertLessEqual(self.app.table_font.measure(narrow),
                             self.app.record_table.column("备注", "width") - hotel.CELL_TEXT_PAD)
        self.resize(1920)
        wide = self.app.record_table.set(item, "备注")
        self.assertGreater(len(wide), len(narrow))
        self.assertEqual(self.app.displayed_records[0]["备注"], self.note)
        self.assertEqual(self.app.entries["备注"].get(), self.note)
        self.assertEqual(self.app.note_detail.get("1.0", "end-1c"), self.note)
        self.assertEqual(str(self.app.note_detail.cget("state")), "disabled")

    def test_short_note_is_restored_when_table_widens(self):
        note = "春节涨价，平常价格为184元。"
        self.records[0]["备注"] = note
        hotel.write_markdown_records(self.records)
        self.app.refresh_table()
        self.resize(1360)
        item = self.select(0)
        self.assertTrue(self.app.record_table.set(item, "备注").endswith("…"))
        self.resize(1920)
        self.assertEqual(self.app.record_table.set(item, "备注"), note)

    def test_copy_uses_full_note_and_detail_is_read_only(self):
        self.select(0)
        with patch.object(self.root, "clipboard_clear") as clear, patch.object(self.root, "clipboard_append") as append:
            self.app.copy_note_button.invoke()
            clear.assert_called_once_with()
            append.assert_called_once_with(self.note)
        self.app.note_detail.insert("1.0", "不应写入")
        self.assertEqual(self.app.note_detail.get("1.0", "end-1c"), self.note)
        self.app.note_detail.tag_add(tk.SEL, "1.0", "1.4")
        self.assertEqual(self.app.note_detail.get(tk.SEL_FIRST, tk.SEL_LAST), self.note[:4])

    def test_detail_resets_for_empty_selection_and_year_change(self):
        self.assertFalse(self.app.note_detail.winfo_ismapped())
        table_height_without_detail = self.app.record_table.winfo_height()
        self.select(0)
        self.assertTrue(self.app.note_detail.winfo_ismapped())
        self.assertLess(self.app.record_table.winfo_height(), table_height_without_detail)
        self.select(1)
        self.assertTrue(self.app.note_detail.winfo_ismapped())
        self.assertEqual(self.app.note_detail.get("1.0", "end-1c"), "这条记录没有备注。")
        self.assertEqual(str(self.app.copy_note_button.cget("state")), "disabled")
        self.select(0)
        self.app.record_table.selection_remove(self.app.record_table.selection())
        self.root.update()
        self.assertFalse(self.app.note_detail.winfo_ismapped())
        self.assertEqual(self.app.note_detail.get("1.0", "end-1c"), "")
        self.assertEqual(self.app.record_table.winfo_height(), table_height_without_detail)
        self.select(0)
        self.assertTrue(self.app.note_detail.winfo_ismapped())
        self.app.choose_year("2025")
        self.root.update()
        self.assertFalse(self.app.note_detail.winfo_ismapped())
        self.assertEqual(self.app.note_detail.get("1.0", "end-1c"), "")

    def test_saving_from_summary_preserves_complete_note(self):
        self.resize(1360)
        self.select(0)
        self.app.entries["总价"].delete(0, tk.END)
        self.app.entries["总价"].insert(0, "600")
        self.app.edit_record()
        self.root.update()
        records, malformed = hotel.parse_markdown_records()
        self.assertEqual(malformed, 0)
        self.assertEqual(records[0]["备注"], self.note)
        self.assertEqual(records[0]["总价"], "600")
        self.assertTrue(self.app.note_detail.winfo_ismapped())
        self.assertEqual(self.app.note_detail.get("1.0", "end-1c"), self.note)


if __name__ == "__main__":
    hotel.enable_high_dpi()
    unittest.main()
