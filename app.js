let workouts = [];
function saveWorkouts() {
  localStorage.setItem("workouts", JSON.stringify(workouts));
}
function loadWorkouts() {
  const savedText = localStorage.getItem("workouts");
  if(savedText !== null) {
    workouts = JSON.parse(savedText);
  }
}


const exerciseInput = document.getElementById("exercise");
const weightInput = document.getElementById("weight");
const repsInput = document.getElementById("reps");
const addButton = document.getElementById("addBtn");
const list = document.getElementById("workoutlist");

function renderList() {
  list.innerHTML = "";

  
  workouts.forEach(function (workout, index) {
    const item = document.createElement("li");
    item.textContent =
      workout.exercise + " — " + workout.weight + " ק״ג × " + workout.reps + " חזרות ";

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "🗑️ מחק";
    deleteButton.addEventListener("click", function () {
      workouts.splice(index, 1); // remove 1 item at this position
      saveWorkouts();            // save the change
      renderList();              // redraw
    });

    item.appendChild(deleteButton);
    list.appendChild(item);
  });
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
    saveWorkouts();
    renderList();
      exerciseInput.value = "";
      weightInput.value = "";
      repsInput.value = "";
}
addButton.addEventListener("click", addWorkout);
loadWorkouts();
renderList();
