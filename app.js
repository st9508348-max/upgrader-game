let workouts = [];

const exerciseInput = document.getElementById("exercise");
const weightInput = document.getElementById("weight");
const repsInput = document.getElementById("reps");
const addButton = document.getElementById("addBtn");
const list = document.getElementById("workoutlist");

function renderList() {

    list.innerHTML = "";

    for(const workout of workouts) {
            const item = document.createElement("li");
    item.textContent =
      workout.exercise + " — " + workout.weight + " ק״ג × " + workout.reps + " חזרות";
    list.appendChild(item);
    }
}
function addWorkout() {
      const exercise = exerciseInput.value;
      const weight = weightInput.value;
      const reps = repsInput.value;
       if (exercise === "") {
    alert("כתוב שם תרגיל");
    return; // "return" means: stop this function right here.
  }
  workouts.push({ exercise: exercise, weight: weight, reps: reps });
    renderList();
      exerciseInput.value = "";
      weightInput.value = "";
      repsInput.value = "";
}
addButton.addEventListener("click", addWorkout);
