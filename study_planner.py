import json
import os
import datetime
import textwrap
import random

DATA_FILE = "data.json"
XP_PER_TASK = 20
XP_TO_LEVEL = 100
class Task:
    def __init__(self, title, category="General", due_date=None, priority=3, notes=""):
        self.id = None  # assigned by Planner
        self.title = title
        self.category = category
        self.due_date = due_date  # string 'YYYY-MM-DD' or None
        self.priority = int(priority)  # 1-high, 5-low
        self.notes = notes
        self.created_at = datetime.datetime.now().isoformat()
        self.completed_at = None

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "due_date": self.due_date,
            "priority": self.priority,
            "notes": self.notes,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @staticmethod
    def from_dict(d):
        t = Task(d["title"], d.get("category", "General"),
                 d.get("due_date"), d.get("priority", 3), d.get("notes", ""))
        t.id = d.get("id")
        t.created_at = d.get("created_at", t.created_at)
        t.completed_at = d.get("completed_at")
        return t


class Planner:
    def __init__(self):
        self.tasks = {}         
        self.completed = {}     
        self.next_id = 1
        self.xp = 0
        self.level = 1
        self.achievements = set()
        self.load()

    
    def load(self):
        if not os.path.exists(DATA_FILE):
            self._create_default_file()
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.next_id = data.get("next_id", 1)
            self.xp = data.get("xp", 0)
            self.level = data.get("level", 1)
            self.achievements = set(data.get("achievements", []))
            self.tasks = {int(k): Task.from_dict(v) for k, v in data.get("tasks", {}).items()}
            self.completed = {int(k): Task.from_dict(v) for k, v in data.get("completed", {}).items()}
            # restore ids inside tasks
            for tid, t in {**self.tasks, **self.completed}.items():
                t.id = tid
        except Exception as e:
            print("Error loading data file:", e)
            print("Creating fresh data file.")
            self._create_default_file()

    def save(self):
        data = {
            "next_id": self.next_id,
            "xp": self.xp,
            "level": self.level,
            "achievements": list(self.achievements),
            "tasks": {tid: task.to_dict() for tid, task in self.tasks.items()},
            "completed": {tid: task.to_dict() for tid, task in self.completed.items()},
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _create_default_file(self):
        self.next_id = 1
        self.xp = 0
        self.level = 1
        self.tasks = {}
        self.completed = {}
        self.achievements = set()
        self.save()

    def add_task(self, title, category="General", due_date=None, priority=3, notes=""):
        t = Task(title, category, due_date, priority, notes)
        t.id = self.next_id
        self.tasks[self.next_id] = t
        self.next_id += 1
        self.save()
        return t.id

    def view_tasks(self, show_completed=False, sort_by="priority"):
        items = list(self.completed.items()) if show_completed else list(self.tasks.items())
        if not items:
            return []
        if sort_by == "priority":
            items.sort(key=lambda x: x[1].priority)
        elif sort_by == "due":
            def due_key(pair):
                d = pair[1].due_date
                return datetime.datetime.fromisoformat(d) if d else datetime.datetime.max
            items.sort(key=due_key)
        else:
            items.sort(key=lambda x: x[0])
        return items

    def get_task(self, task_id):
        return self.tasks.get(task_id) or self.completed.get(task_id)

    def delete_task(self, task_id):
        removed = None
        if task_id in self.tasks:
            removed = self.tasks.pop(task_id)
        elif task_id in self.completed:
            removed = self.completed.pop(task_id)
        self.save()
        return removed

    def edit_task(self, task_id, **kwargs):
        t = self.get_task(task_id)
        if not t:
            return False
        for k, v in kwargs.items():
            if hasattr(t, k) and v is not None:
                setattr(t, k, v)
        self.save()
        return True

    def complete_task(self, task_id):
        if task_id not in self.tasks:
            return False, "Task not found or already completed."
        t = self.tasks.pop(task_id)
        t.completed_at = datetime.datetime.now().isoformat()
        self.completed[task_id] = t
        gained = XP_PER_TASK
        prev_xp = self.xp
        self.xp += gained
        leveled_up = False
        if self.xp // XP_TO_LEVEL + 1 > self.level:
            self.level = self.xp // XP_TO_LEVEL + 1
            leveled_up = True
        self._check_achievements_on_completion()
        self.save()
        return True, {"gained": gained, "leveled_up": leveled_up, "prev_xp": prev_xp}

    def _check_achievements_on_completion(self):
        completed_count = len(self.completed)
        # milestones
        milestones = {1: "First Task Done",
                      5: "Getting Serious",
                      10: "Study Machine",
                      25: "Legendary Studier"}
        for k, name in milestones.items():
            if completed_count >= k and name not in self.achievements:
                self.achievements.add(name)

        # level based achievements
        if self.level >= 2 and "Level 2 Achieved" not in self.achievements:
            self.achievements.add("Level 2 Achieved")
        if self.level >= 5 and "Level 5 Achieved" not in self.achievements:
            self.achievements.add("Level 5 Achieved")

    def stats_summary(self):
        total_tasks = len(self.tasks) + len(self.completed)
        return {
            "pending": len(self.tasks),
            "completed": len(self.completed),
            "total": total_tasks,
            "xp": self.xp,
            "level": self.level,
            "achievements": sorted(list(self.achievements)),
        }

    def search_tasks(self, keyword):
        keyword = keyword.lower()
        results = []
        for d in (self.tasks, self.completed):
            for tid, t in d.items():
                if keyword in t.title.lower() or keyword in t.notes.lower() or keyword in t.category.lower():
                    results.append((tid, t))
        return results


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_header():
    print("=" * 60)
    print("   STUDY PLANNER  -  Level up as you study! ".center(60))
    print("=" * 60)

def nice_wrap(text, width=56):
    return textwrap.fill(text, width=width)

def show_motivational(level_up=False):
    messages = [
        "Nice! Keep the momentum 🚀",
        "Small steps every day lead to big results 💪",
        "You are one task closer to your goal ✨",
        "Consistency beats intensity. Keep going!",
        "Study hard, play hard. Balance is key 😉"
    ]
    print("\n" + random.choice(messages))
    if level_up:
        print("\n✨ CONGRATS! You leveled up! ✨\n")

def prompt_date(prompt_text="Due date (YYYY-MM-DD) or leave blank: "):
    s = input(prompt_text).strip()
    if s == "":
        return None
    try:
        # validate date format
        datetime.date.fromisoformat(s)
        return s
    except Exception:
        print("Invalid date format. Use YYYY-MM-DD.")
        return prompt_date(prompt_text)

def prompt_priority():
    try:
        p = int(input("Priority (1=High ... 5=Low) [3]: ") or "3")
        if p < 1 or p > 5:
            raise ValueError
        return p
    except ValueError:
        print("Enter number between 1 and 5.")
        return prompt_priority()

def wait_enter():
    input("\nPress Enter to continue...")

def cmd_add(planner):
    clear_screen()
    print_header()
    print("Add a new task\n")
    title = input("Title: ").strip()
    if not title:
        print("Task title cannot be empty.")
        wait_enter()
        return
    category = input("Category (e.g., Study, Revision, Project) [General]: ").strip() or "General"
    due = prompt_date()
    priority = prompt_priority()
    notes = input("Notes (optional): ").strip()
    tid = planner.add_task(title, category, due, priority, notes)
    print(f"\nTask added with ID: {tid}")
    wait_enter()

def cmd_view(planner, show_completed=False):
    clear_screen()
    print_header()
    print("Completed Tasks\n" if show_completed else "Pending Tasks\n")
    items = planner.view_tasks(show_completed=show_completed)
    if not items:
        print("No tasks to show.")
    else:
        for tid, t in items:
            due = f"Due: {t.due_date}" if t.due_date else "No due"
            status = f"Completed at {t.completed_at}" if t.completed_at else "Pending"
            print(f"[{tid}] {t.title} ({t.category}) - P{t.priority} - {due}")
            if t.notes:
                print("    " + nice_wrap("Notes: " + t.notes))
            print("    " + status)
            print("-" * 50)
    wait_enter()

def cmd_complete(planner):
    clear_screen()
    print_header()
    print("Mark Task as Completed\n")
    try:
        tid = int(input("Enter task ID to complete: "))
    except ValueError:
        print("Invalid ID.")
        wait_enter()
        return
    ok, result = planner.complete_task(tid)
    if not ok:
        print(result)
    else:
        gained = result["gained"]
        if result["leveled_up"]:
            print(f"You gained {gained} XP and leveled up! 🎉")
            show_motivational(level_up=True)
        else:
            print(f"You gained {gained} XP.")
            show_motivational(False)
    wait_enter()

def cmd_delete(planner):
    clear_screen()
    print_header()
    print("Delete a task\n")
    try:
        tid = int(input("Enter task ID to delete: "))
    except ValueError:
        print("Invalid ID.")
        wait_enter()
        return
    removed = planner.delete_task(tid)
    if removed:
        print("Task removed.")
    else:
        print("Task not found.")
    wait_enter()

def cmd_edit(planner):
    clear_screen()
    print_header()
    print("Edit a task\n")
    try:
        tid = int(input("Enter task ID to edit: "))
    except ValueError:
        print("Invalid ID.")
        wait_enter()
        return
    t = planner.get_task(tid)
    if not t:
        print("Task not found.")
        wait_enter()
        return
    print(f"Editing [{t.id}] {t.title}")
    new_title = input(f"New Title (leave blank to keep) [{t.title}]: ").strip() or t.title
    new_category = input(f"New Category [{t.category}]: ").strip() or t.category
    new_due = prompt_date(f"New due date (YYYY-MM-DD) or blank [{t.due_date}]: ")
    if new_due is None:
        new_due = t.due_date
    new_priority = input(f"New Priority (1-5) [{t.priority}]: ").strip()
    new_priority = int(new_priority) if new_priority else t.priority
    new_notes = input("New notes (leave blank to keep): ").strip() or t.notes
    planner.edit_task(tid, title=new_title, category=new_category, due_date=new_due, priority=new_priority, notes=new_notes)
    print("Task updated.")
    wait_enter()

def cmd_stats(planner):
    clear_screen()
    print_header()
    s = planner.stats_summary()
    print("Your Stats\n")
    print(f"Level: {s['level']}    XP: {s['xp']} / {s['level'] * XP_TO_LEVEL}")
    print(f"Pending tasks: {s['pending']}    Completed tasks: {s['completed']}")
    print(f"Total tasks: {s['total']}")
    print("\nAchievements:")
    if s["achievements"]:
        for a in s["achievements"]:
            print(" - " + a)
    else:
        print(" No achievements yet. Complete tasks to unlock!")
    # small progress bar to next level
    xp = s['xp']
    xp_to_next = (s['level'] * XP_TO_LEVEL) - xp
    progress = xp % XP_TO_LEVEL
    print("\nProgress to next level:")
    bar_len = 30
    filled = int((progress / XP_TO_LEVEL) * bar_len)
    print("[" + "#" * filled + "-" * (bar_len - filled) + f"] {progress}/{XP_TO_LEVEL} XP")
    wait_enter()

def cmd_search(planner):
    clear_screen()
    print_header()
    print("Search Tasks\n")
    q = input("Enter keyword to search: ").strip()
    if not q:
        print("Empty search.")
        wait_enter()
        return
    results = planner.search_tasks(q)
    if not results:
        print("No matching tasks.")
    else:
        for tid, t in results:
            status = "Completed" if tid in planner.completed else "Pending"
            print(f"[{tid}] {t.title} ({t.category}) - {status}")
            if t.notes:
                print("    " + nice_wrap("Notes: " + t.notes))
            print("-" * 40)
    wait_enter()

def cmd_quick_add(planner):
    # fast add using minimal input
    title = input("Quick add - title: ").strip()
    if not title:
        print("Cancelled.")
        wait_enter()
        return
    tid = planner.add_task(title)
    print(f"Task added with ID {tid}")
    wait_enter()

def cmd_export(planner):
    clear_screen()
    print_header()
    print("Export Tasks (to tasks_export.json)\n")
    export = {
        "tasks": {tid: t.to_dict() for tid, t in planner.tasks.items()},
        "completed": {tid: t.to_dict() for tid, t in planner.completed.items()},
        "xp": planner.xp,
        "level": planner.level,
        "achievements": list(planner.achievements)
    }
    with open("tasks_export.json", "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)
    print("Export complete.")
    wait_enter()

def main_menu():
    planner = Planner()
    while True:
        clear_screen()
        print_header()
        print(f"Level: {planner.level}    XP: {planner.xp}    Pending: {len(planner.tasks)}    Completed: {len(planner.completed)}")
        print("-" * 60)
        print("1. Add Task")
        print("2. Quick Add Task")
        print("3. View Pending Tasks")
        print("4. View Completed Tasks")
        print("5. Complete a Task")
        print("6. Edit a Task")
        print("7. Delete a Task")
        print("8. Stats & Achievements")
        print("9. Search Tasks")
        print("10. Export tasks")
        print("0. Exit")
        print("-" * 60)
        choice = input("Choose an option: ").strip()
        if choice == "1":
            cmd_add(planner)
        elif choice == "2":
            cmd_quick_add(planner)
        elif choice == "3":
            cmd_view(planner, show_completed=False)
        elif choice == "4":
            cmd_view(planner, show_completed=True)
        elif choice == "5":
            cmd_complete(planner)
        elif choice == "6":
            cmd_edit(planner)
        elif choice == "7":
            cmd_delete(planner)
        elif choice == "8":
            cmd_stats(planner)
        elif choice == "9":
            cmd_search(planner)
        elif choice == "10":
            cmd_export(planner)
        elif choice == "0":
            print("Saving and exiting... Goodbye 👋")
            planner.save()
            break
        else:
            print("Invalid choice.")
            wait_enter()

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting. Have a good day!")
