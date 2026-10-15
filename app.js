let workouts = [];

// Load the workout list from the server when the page opens.
async function loadWorkouts() {
  const response = await fetch("/api/workouts");
  if (!response.ok) {
    throw new Error("Could not load workouts");
  }
  workouts = await response.json();
  renderList();
}


const exerciseInput = document.getElementById("exercise");
const weightInput = document.getElementById("weight");
const repsInput = document.getElementById("reps");
const addButton = document.getElementById("addBtn");
const list = document.getElementById("workoutlist");

// Rebuild the list so the screen matches the current workout data.
function renderList() {
  list.innerHTML = "";

  
  workouts.forEach(function (workout) {
    const item = document.createElement("li");
    item.textContent =
      workout.exercise + " — " + workout.weight + " ק״ג × " + workout.reps + " חזרות ";

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "🗑️ מחק";
    deleteButton.addEventListener("click", async function () {
      const response = await fetch(`/api/workouts/${workout.id}`, {
        method: "DELETE"
      });
      if (!response.ok) {
        alert("מחיקת האימון נכשלה");
        return;
      }
      workouts = workouts.filter((currentWorkout) => currentWorkout.id !== workout.id);
      renderList();
    });

    item.appendChild(deleteButton);
    list.appendChild(item);
  });
}

// Send a new workout to the server, then refresh the displayed list.
async function addWorkout() {
  const exercise = exerciseInput.value;
  const weight = weightInput.value;
  const reps = repsInput.value;
  if (exercise === "") {
    alert("כתוב שם תרגיל");
    return;
  }

  const response = await fetch("/api/workouts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ exercise: exercise, weight: weight, reps: reps })
  });
  if (!response.ok) {
    alert("שמירת האימון נכשלה");
    return;
  }

  workouts.push(await response.json());
  renderList();
  exerciseInput.value = "";
  weightInput.value = "";
  repsInput.value = "";
}

// Connect the page controls to the workout functions.
addButton.addEventListener("click", addWorkout);
loadWorkouts().catch(function () {
  alert("טעינת האימונים נכשלה");
});
