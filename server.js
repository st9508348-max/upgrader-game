const http = require("http");
const fs = require("fs");
const path = require("path");

const port = 3000;
const dataFile = path.join(__dirname, "workouts.json");

// Load saved workouts, treating a missing data file as an empty list.
function readWorkouts() {
	try {
		return JSON.parse(fs.readFileSync(dataFile, "utf8"));
	} catch (error) {
		if (error.code === "ENOENT") return [];
		throw error;
	}
}

// Persist the complete workout list as formatted JSON.
function writeWorkouts(workouts) {
	fs.writeFileSync(dataFile, JSON.stringify(workouts, null, 2));
}

// Send a JSON response with the requested status code.
function sendJson(response, statusCode, body) {
	response.writeHead(statusCode, { "Content-Type": "application/json" });
	response.end(JSON.stringify(body));
}

// Serve one of the static files used by the browser app.
function serveFile(response, fileName, contentType) {
	fs.readFile(path.join(__dirname, fileName), (error, content) => {
		if (error) {
			sendJson(response, 404, { error: "File not found" });
			return;
		}
		response.writeHead(200, { "Content-Type": contentType });
		response.end(content);
	});
}

// Route API requests and serve the frontend files.
const server = http.createServer((request, response) => {
	if (request.method === "GET" && request.url === "/api/workouts") {
		sendJson(response, 200, readWorkouts());
		return;
	}

	if (request.method === "POST" && request.url === "/api/workouts") {
		let body = "";
		request.on("data", (chunk) => { body += chunk; });
		request.on("end", () => {
			try {
				const workout = JSON.parse(body);
				if (!workout.exercise) {
					sendJson(response, 400, { error: "exercise is required" });
					return;
				}

				const workouts = readWorkouts();
				const savedWorkout = {
					id: Date.now(),
					exercise: String(workout.exercise),
					weight: String(workout.weight || ""),
					reps: String(workout.reps || "")
				};
				workouts.push(savedWorkout);
				writeWorkouts(workouts);
				sendJson(response, 201, savedWorkout);
			} catch (error) {
				sendJson(response, 400, { error: "Invalid JSON" });
			}
		});
		return;
	}

	if (request.method === "DELETE" && request.url.startsWith("/api/workouts/")) {
		const id = Number(request.url.split("/").pop());
		const workouts = readWorkouts();
		const remaining = workouts.filter((workout) => workout.id !== id);
		if (remaining.length === workouts.length) {
			sendJson(response, 404, { error: "Workout not found" });
			return;
		}
		writeWorkouts(remaining);
		sendJson(response, 200, { ok: true });
		return;
	}

	if (request.method === "GET" && request.url === "/") {
		serveFile(response, "index.html", "text/html; charset=utf-8");
		return;
	}

	if (request.method === "GET" && request.url === "/app.js") {
		serveFile(response, "app.js", "text/javascript; charset=utf-8");
		return;
	}

	sendJson(response, 404, { error: "Not found" });
});

server.listen(port, () => {
	console.log(`Gym server running at http://localhost:${port}`);
});
