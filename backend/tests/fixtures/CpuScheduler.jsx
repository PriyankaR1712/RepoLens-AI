
import { useState } from "react";
import "./CpuScheduler.css";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const ALGORITHMS = [
  {
    id: "fcfs",
    label: "FCFS",
    description: "First Come, First Served",
  },
  {
    id: "sjf",
    label: "SJF",
    description: "Shortest Job First",
  },
  {
    id: "srtf",
    label: "SRTF",
    description: "Shortest Remaining Time",
  },
  {
    id: "priority",
    label: "Priority",
    description: "Priority-based execution",
  },
  {
    id: "round_robin",
    label: "Round Robin",
    description: "Time-slice based execution",
  },
];

const INITIAL_PROCESSES = [
  { process_id: "P1", arrival_time: 0, burst_time: 5, priority: 2 },
  { process_id: "P2", arrival_time: 1, burst_time: 3, priority: 1 },
  { process_id: "P3", arrival_time: 2, burst_time: 2, priority: 3 },
];

function CpuScheduler() {
  const [processes, setProcesses] = useState(INITIAL_PROCESSES);
  const [selectedAlgorithms, setSelectedAlgorithms] = useState([
    "fcfs",
    "sjf",
    "srtf",
    "priority",
    "round_robin",
  ]);
  const [quantum, setQuantum] = useState(2);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSimulated, setHasSimulated] = useState(false);

  const updateProcess = (index, field, value) => {
    setProcesses((previous) =>
      previous.map((process, i) =>
        i === index
          ? {
              ...process,
              [field]: field === "process_id" ? value : value,
            }
          : process
      )
    );
  };

  const addProcess = () => {
    const nextNumber = processes.length + 1;

    setProcesses((previous) => [
      ...previous,
      {
        process_id: `P${nextNumber}`,
        arrival_time: 0,
        burst_time: 1,
        priority: 1,
      },
    ]);
    setResults([]);
    setHasSimulated(false);
  };

  const removeProcess = (index) => {
    if (processes.length === 1) return;

    setProcesses((previous) => previous.filter((_, i) => i !== index));
    setResults([]);
    setHasSimulated(false);
  };

  const toggleAlgorithm = (algorithmId) => {
    setSelectedAlgorithms((previous) =>
      previous.includes(algorithmId)
        ? previous.filter((item) => item !== algorithmId)
        : [...previous, algorithmId]
    );
    setResults([]);
    setHasSimulated(false);
  };

  const simulate = async () => {
    setError("");
    setResults([]);

    if (processes.length === 0) {
      setError("Add at least one process.");
      return;
    }

    if (selectedAlgorithms.length === 0) {
      setError("Select at least one scheduling algorithm.");
      return;
    }

    const ids = processes.map((p) => p.process_id.trim());

    if (ids.some((id) => !id)) {
      setError("Process IDs cannot be empty.");
      return;
    }

    if (new Set(ids).size !== ids.length) {
      setError("Process IDs must be unique.");
      return;
    }

    if (
      processes.some(
        (p) =>
          !Number.isInteger(Number(p.arrival_time)) ||
          Number(p.arrival_time) < 0 ||
          !Number.isInteger(Number(p.burst_time)) ||
          Number(p.burst_time) <= 0 ||
          !Number.isInteger(Number(p.priority))
      )
    ) {
      setError("Enter valid whole numbers. Arrival must be 0 or more and burst must be greater than 0.");
      return;
    }

    if (
      selectedAlgorithms.includes("round_robin") &&
      (!Number.isInteger(Number(quantum)) || Number(quantum) <= 0)
    ) {
      setError("Time quantum must be a positive whole number.");
      return;
    }

    const payload = {
      processes: processes.map((p) => ({
        process_id: p.process_id.trim(),
        arrival_time: Number(p.arrival_time),
        burst_time: Number(p.burst_time),
        priority: Number(p.priority),
      })),
      algorithms: selectedAlgorithms,
      quantum: Number(quantum),
    };

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/scheduling/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Simulation failed. Check your inputs."
        );
      }

      setResults(data.results);
      setHasSimulated(true);
    } catch (err) {
      setError(err.message || "Could not connect to the scheduling API.");
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (value) =>
    Number(value).toFixed(2).replace(/\.00$/, "");

  const getProcessColor = (processId) => {
    if (!processId) return "idle";

    const number = Number(processId.replace(/\D/g, "")) || 1;
    return `process-color-${((number - 1) % 6) + 1}`;
  };

  return (
    <div className="cpu-scheduler">
      <div className="scheduler-heading">
        <div>
          <span className="section-eyebrow">OPERATING SYSTEMS LAB</span>
          <h1>CPU Scheduling Simulator</h1>
          <p>
            Visualize process execution, compare scheduling algorithms,
            and analyze performance metrics.
          </p>
        </div>
        <div className="scheduler-live-badge">
          <span /> Simulation Engine
        </div>
      </div>

      <section className="scheduler-panel">
        <div className="scheduler-panel-heading">
          <div>
            <h2>Process Configuration</h2>
            <p>Define the processes entering the CPU scheduler.</p>
          </div>
          <button className="scheduler-secondary-btn" onClick={addProcess}>
            + Add Process
          </button>
        </div>

        <div className="scheduler-table-wrapper">
          <table className="scheduler-input-table">
            <thead>
              <tr>
                <th>Process ID</th>
                <th>Arrival Time</th>
                <th>Burst Time</th>
                <th>Priority</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {processes.map((process, index) => (
                <tr key={`${index}-${process.process_id}`}>
                  <td>
                    <input
                      value={process.process_id}
                      onChange={(e) =>
                        updateProcess(index, "process_id", e.target.value)
                      }
                      aria-label={`Process ${index + 1} ID`}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="0"
                      value={process.arrival_time}
                      onChange={(e) =>
                        updateProcess(index, "arrival_time", e.target.value)
                      }
                      aria-label={`Process ${index + 1} arrival time`}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      min="1"
                      value={process.burst_time}
                      onChange={(e) =>
                        updateProcess(index, "burst_time", e.target.value)
                      }
                      aria-label={`Process ${index + 1} burst time`}
                    />
                  </td>
                  <td>
                    <input
                      type="number"
                      value={process.priority}
                      onChange={(e) =>
                        updateProcess(index, "priority", e.target.value)
                      }
                      aria-label={`Process ${index + 1} priority`}
                    />
                  </td>
                  <td>
                    <button
                      className="scheduler-delete-btn"
                      onClick={() => removeProcess(index)}
                      disabled={processes.length === 1}
                      aria-label={`Remove process ${process.process_id}`}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="scheduler-hint">
          Lower priority number means higher priority. Priority is used only
          by Priority Scheduling.
        </p>
      </section>

      <section className="scheduler-panel">
        <div className="scheduler-panel-heading">
          <div>
            <h2>Scheduling Algorithms</h2>
            <p>Select one or more algorithms to compare.</p>
          </div>
        </div>

        <div className="algorithm-options">
          {ALGORITHMS.map((algorithm, index) => (
            <label
              key={algorithm.id}
              className={`algorithm-option ${
                selectedAlgorithms.includes(algorithm.id) ? "selected" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={selectedAlgorithms.includes(algorithm.id)}
                onChange={() => toggleAlgorithm(algorithm.id)}
              />

              <span className="algorithm-card-top">
                <span className="algorithm-number">
                  0{index + 1}
                </span>
                <span className="algorithm-check" />
              </span>

              <span className="algorithm-copy">
                <strong>{algorithm.label}</strong>
                <small>{algorithm.description}</small>
              </span>
            </label>
          ))}
        </div>

        {selectedAlgorithms.includes("round_robin") && (
          <div className="quantum-control">
            <label htmlFor="time-quantum">Time Quantum</label>
            <input
              id="time-quantum"
              type="number"
              min="1"
              value={quantum}
              onChange={(e) => setQuantum(e.target.value)}
            />
          </div>
        )}

        <div className="scheduler-actions">
          <button
            className="scheduler-primary-btn"
            onClick={simulate}
            disabled={loading}
          >
            {loading ? "Running Simulation..." : "Run Simulation →"}
          </button>
        </div>

        {error && <div className="scheduler-error">{error}</div>}
      </section>

      {hasSimulated && results.length > 0 && (
        <section className="scheduler-results">
          <div className="scheduler-results-heading">
            <div>
              <span className="section-eyebrow">ANALYSIS</span>
              <h2>Simulation Results</h2>
              <p>
                Compare execution timelines and performance across algorithms.
              </p>
            </div>
            <span className="results-count">
              {results.length} algorithm{results.length > 1 ? "s" : ""}
            </span>
          </div>

          {results.map((result) => {
            const totalTime = Math.max(
              ...result.gantt_chart.map((segment) => segment.end),
              1
            );

            return (
              <article className="result-card" key={result.algorithm}>
                <div className="result-card-heading">
                  <h3>{result.algorithm}</h3>
                  <span>
                    Average Waiting Time:{" "}
                    <strong>
                      {formatNumber(result.averages.waiting_time)}
                    </strong>
                  </span>
                </div>

                <div className="gantt-section">
                  <h4>Gantt Chart</h4>
                  <div className="gantt-scroll">
                    <div className="gantt-chart">
                      {result.gantt_chart.map((segment, index) => (
                        <div
                          key={`${segment.start}-${index}`}
                          className={`gantt-block ${getProcessColor(
                            segment.process_id
                          )}`}
                          style={{
                            width: `${Math.max(
                              ((segment.end - segment.start) / totalTime) *
                                100,
                              2
                            )}%`,
                          }}
                          title={`${segment.process_id || "Idle"}: ${segment.start}–${segment.end}`}
                        >
                          <span>{segment.process_id || "Idle"}</span>
                        </div>
                      ))}
                    </div>
                    <div className="gantt-timeline">
                      {result.gantt_chart.map((segment, index) => (
                        <span
                          key={`${segment.start}-time-${index}`}
                          style={{
                            left: `${(segment.start / totalTime) * 100}%`,
                          }}
                        >
                          {segment.start}
                        </span>
                      ))}
                      <span className="gantt-end-time">{totalTime}</span>
                    </div>
                  </div>
                </div>

                <div className="metric-grid">
                  <div className="metric-item">
                    <span>Avg. Completion Time</span>
                    <strong>
                      {formatNumber(result.averages.completion_time)}
                    </strong>
                  </div>
                  <div className="metric-item">
                    <span>Avg. Turnaround Time</span>
                    <strong>
                      {formatNumber(result.averages.turnaround_time)}
                    </strong>
                  </div>
                  <div className="metric-item">
                    <span>Avg. Waiting Time</span>
                    <strong>
                      {formatNumber(result.averages.waiting_time)}
                    </strong>
                  </div>
                  <div className="metric-item">
                    <span>Avg. Response Time</span>
                    <strong>
                      {formatNumber(result.averages.response_time)}
                    </strong>
                  </div>
                </div>

                <div className="scheduler-table-wrapper">
                  <table className="scheduler-metrics-table">
                    <thead>
                      <tr>
                        <th>Process</th>
                        <th>Arrival</th>
                        <th>Burst</th>
                        <th>Completion</th>
                        <th>Turnaround</th>
                        <th>Waiting</th>
                        <th>Response</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.processes.map((process) => (
                        <tr key={process.process_id}>
                          <td>
                            <strong>{process.process_id}</strong>
                          </td>
                          <td>{process.arrival_time}</td>
                          <td>{process.burst_time}</td>
                          <td>{process.completion_time}</td>
                          <td>{process.turnaround_time}</td>
                          <td>{process.waiting_time}</td>
                          <td>{process.response_time}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
}

export default CpuScheduler;
