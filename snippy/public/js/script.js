document.addEventListener("DOMContentLoaded", function () {
  console.log("Jester Research Tool loaded");

  // Year range selector
  const yearRangeSelect = document.getElementById("yearRange");
  const customYearRange = document.getElementById("customYearRange");

  if (yearRangeSelect) {
    yearRangeSelect.addEventListener("change", function () {
      if (this.value === "custom") {
        customYearRange.style.display = "block";
      } else {
        customYearRange.style.display = "none";
      }
    });
  }

  // JUFO threshold selector
  const targetJufoSelect = document.getElementById("targetJufo");
  const customTargetJufo = document.getElementById("customTargetJufo");

  if (targetJufoSelect) {
    targetJufoSelect.addEventListener("change", function () {
      if (this.value === "custom") {
        customTargetJufo.style.display = "block";
      } else {
        customTargetJufo.style.display = "none";
      }
    });
  }

  // Search form submission
  const searchForm = document.getElementById("searchForm");
  const searchBtn = document.getElementById("searchBtn");
  const stopBtn = document.getElementById("stopBtn");
  const progressBar = document.getElementById("progress-bar");
  const progressText = document.getElementById("progress-text");
  const jufoCountText = document.getElementById("jufo-count");
  const downloadBtn = document.getElementById("downloadBtn");
  const resultsTable = document.getElementById("resultsTable");

  // Flag to track if search is in progress
  let searchInProgress = false;
  let shouldStopSearch = false;

  if (searchForm) {
    searchForm.addEventListener("submit", function (e) {
      e.preventDefault();

      if (searchInProgress) {
        return;
      }

      // Get form data
      const formData = new FormData(searchForm);
      const searchData = {
        keywords: formData.get("keywords"),
        max_articles: formData.get("max_articles"),
        year_range: formData.get("year_range"),
        target_jufo: formData.get("target_jufo"),
      };

      // Handle custom year range
      if (searchData.year_range === "custom") {
        const yearStart = formData.get("year_start");
        const yearEnd = formData.get("year_end");
        if (yearStart && yearEnd) {
          searchData.year_range = `${yearStart}-${yearEnd}`;
        }
      }

      // Handle custom JUFO threshold
      if (searchData.target_jufo === "custom") {
        searchData.target_jufo = formData.get("custom_target_jufo");
      }

      // Reset UI for new search
      resetSearchUI();
      startSearch(searchData);
    });
  }

  // Stop button
  if (stopBtn) {
    stopBtn.addEventListener("click", function () {
      shouldStopSearch = true;
      stopBtn.disabled = true;
      stopBtn.textContent = "Stopping...";
      progressText.textContent = "Stopping search...";
    });
  }

  // Function to reset search UI
  function resetSearchUI() {
    if (resultsTable) {
      const tbody = resultsTable.querySelector("tbody");
      tbody.innerHTML = "";
    }

    if (progressBar) {
      progressBar.style.width = "0%";
      progressBar.setAttribute("aria-valuenow", "0");
      progressText.textContent = "Starting search...";
      jufoCountText.textContent = "JUFO 2/3: 0";
    }

    if (downloadBtn) {
      downloadBtn.style.display = "none";
    }

    if (searchBtn) {
      searchBtn.disabled = true;
    }

    if (stopBtn) {
      shouldStopSearch = false;
      stopBtn.style.display = "block";
      stopBtn.disabled = false;
      stopBtn.textContent = "Stop";
    }

    searchInProgress = true;
  }

  // Function to update UI after search completes
  function finishSearchUI() {
    searchInProgress = false;

    if (searchBtn) {
      searchBtn.disabled = false;
    }

    if (stopBtn) {
      stopBtn.style.display = "none";
    }

    if (
      downloadBtn &&
      resultsTable &&
      resultsTable.querySelector("tbody").children.length > 0
    ) {
      downloadBtn.style.display = "block";
    }

    progressText.textContent = "Search complete";
  }

  // Function to start search
  async function startSearch(searchData) {
    try {
      // Initial search request
      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(searchData),
      });

      if (!response.ok) {
        throw new Error("Search request failed");
      }

      const data = await response.json();

      // Update results table with initial results
      updateResultsTable(data.initial_results);

      // Update progress
      updateProgress(data.count, searchData.max_articles, data.jufo_count);

      // If we need to fetch more results and should not stop
      if (data.has_more && !shouldStopSearch) {
        await fetchMoreResults(
          searchData,
          data.next_offset,
          data.count,
          searchData.max_articles
        );
      } else {
        finishSearchUI();
      }
    } catch (error) {
      console.error("Error during search:", error);
      progressText.textContent = "Error: " + error.message;
      finishSearchUI();
    }
  }

  // Function to fetch more search results
  async function fetchMoreResults(searchData, offset, totalCount, maxArticles) {
    try {
      // Check if we should stop
      if (shouldStopSearch || totalCount >= maxArticles) {
        finishSearchUI();
        return;
      }

      // Fetch next batch
      const response = await fetch("/api/search/more", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          keywords: searchData.keywords,
          offset: offset,
          batch_size: 20,
          year_range: searchData.year_range,
          target_jufo: searchData.target_jufo,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch more results");
      }

      const data = await response.json();

      // Update results table with new results
      updateResultsTable(data.new_results);

      // Update progress
      updateProgress(data.count, maxArticles, data.jufo_count);

      // If we need to fetch more results and should not stop
      if (data.has_more && !shouldStopSearch && data.count < maxArticles) {
        await fetchMoreResults(
          searchData,
          data.next_offset,
          data.count,
          maxArticles
        );
      } else {
        finishSearchUI();
      }
    } catch (error) {
      console.error("Error fetching more results:", error);
      progressText.textContent = "Error: " + error.message;
      finishSearchUI();
    }
  }

  // Function to update results table
  function updateResultsTable(results) {
    if (!resultsTable) return;

    const tbody = resultsTable.querySelector("tbody");

    results.forEach((result) => {
      const tr = document.createElement("tr");

      // Set class based on JUFO level
      if (result.level == 3) {
        tr.classList.add("table-primary");
      } else if (result.level == 2) {
        tr.classList.add("table-info");
      } else if (result.level == 1) {
        tr.classList.add("table-light");
      }

      // Create table cells
      tr.innerHTML = `
        <td>${result.title}</td>
        <td>${result.journal}</td>
        <td>${result.year}</td>
        <td>${result.level !== null ? result.level : "Not ranked"}</td>
        <td>
          ${
            result.link && result.link !== "No link available"
              ? `<a href="${result.link}" target="_blank" class="btn btn-sm btn-primary">Article</a>`
              : `<span>No Link</span>`
          }
        </td>
      `;

      tbody.appendChild(tr);
    });
  }

  // Function to update progress UI
  function updateProgress(count, max, jufoCount) {
    if (!progressBar) return;

    const percentage = Math.min(Math.round((count / max) * 100), 100);

    progressBar.style.width = percentage + "%";
    progressBar.setAttribute("aria-valuenow", percentage);
    progressText.textContent = `Found ${count} of max ${max} articles`;
    jufoCountText.textContent = `JUFO 2/3: ${jufoCount}`;
  }

  // JUFO filter functionality
  const jufoFilter = document.getElementById("jufoFilter");

  if (jufoFilter) {
    jufoFilter.addEventListener("change", function () {
      filterTableByJufo(this.value);
    });
  }

  // Function to filter table by JUFO level
  function filterTableByJufo(level) {
    if (!resultsTable) return;

    const rows = resultsTable.querySelectorAll("tbody tr");

    rows.forEach((row) => {
      const jufoCell = row.querySelector("td:nth-child(4)");
      const jufoValue = jufoCell.textContent.trim();

      if (level === "all") {
        row.style.display = "";
      } else if (level === "2_3") {
        row.style.display =
          jufoValue === "2" || jufoValue === "3" ? "" : "none";
      } else if (level === "3") {
        row.style.display = jufoValue === "3" ? "" : "none";
      } else if (level === "2") {
        row.style.display = jufoValue === "2" ? "" : "none";
      } else if (level === "1") {
        row.style.display = jufoValue === "1" ? "" : "none";
      } else if (level === "0") {
        row.style.display = jufoValue === "0" ? "" : "none";
      } else if (level === "not_ranked") {
        row.style.display = jufoValue === "Not ranked" ? "" : "none";
      }
    });
  }

  // Sorting functionality
  const sortableHeaders = document.querySelectorAll(".sortable");

  if (sortableHeaders.length > 0) {
    sortableHeaders.forEach((header) => {
      header.addEventListener("click", function () {
        const column = this.getAttribute("data-sort");
        const isAsc = this.classList.contains("asc");

        // Reset all headers
        sortableHeaders.forEach((h) => {
          h.classList.remove("asc", "desc");
        });

        // Set new sort direction
        this.classList.add(isAsc ? "desc" : "asc");

        // Sort the table
        sortTable(column, !isAsc);
      });
    });
  }

  // Function to sort table
  function sortTable(column, asc) {
    if (!resultsTable) return;

    const tbody = resultsTable.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("tr"));

    // Define column index based on column name
    const columnMap = {
      title: 0,
      journal: 1,
      year: 2,
      level: 3,
    };

    const columnIndex = columnMap[column];

    // Sort rows
    rows.sort((a, b) => {
      let valueA = a.cells[columnIndex].textContent.trim();
      let valueB = b.cells[columnIndex].textContent.trim();

      // Special handling for JUFO level
      if (column === "level") {
        valueA = valueA === "Not ranked" ? -1 : parseInt(valueA);
        valueB = valueB === "Not ranked" ? -1 : parseInt(valueB);
      }

      // Special handling for year
      if (column === "year") {
        valueA = valueA === "N/A" ? 0 : parseInt(valueA);
        valueB = valueB === "N/A" ? 0 : parseInt(valueB);
      }

      if (valueA < valueB) {
        return asc ? -1 : 1;
      }
      if (valueA > valueB) {
        return asc ? 1 : -1;
      }
      return 0;
    });

    // Reattach sorted rows
    rows.forEach((row) => {
      tbody.appendChild(row);
    });
  }

  // Download CSV button
  if (downloadBtn) {
    downloadBtn.addEventListener("click", function () {
      const keywords = document
        .querySelector(".centered-title")
        ?.getAttribute("data-keywords");

      if (keywords) {
        window.location.href =
          "/api/history/" + encodeURIComponent(keywords) + "/download";
      } else {
        // If not from history, use the current search keywords
        const searchKeywords = document.querySelector(
          "input[name='keywords']"
        )?.value;
        if (searchKeywords) {
          window.location.href =
            "/download/" + encodeURIComponent(searchKeywords);
        }
      }
    });
  }

  // Delete article button for history page
  const deleteArticleBtns = document.querySelectorAll(".delete-article-btn");

  if (deleteArticleBtns.length > 0) {
    deleteArticleBtns.forEach((btn) => {
      btn.addEventListener("click", function (e) {
        e.preventDefault();

        if (!confirm("Are you sure you want to delete this article?")) {
          return;
        }

        const keywords = this.getAttribute("data-keywords");
        const link = this.getAttribute("data-link");

        fetch("/api/history/article", {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            keywords: keywords,
            link: link,
          }),
        })
          .then((response) => {
            if (!response.ok) throw new Error("Failed to delete article");
            return response.json();
          })
          .then((data) => {
            if (data.status === "success") {
              // Remove row from table
              const row = this.closest("tr");
              if (row) {
                row.remove();
              }
            } else {
              alert(
                "Failed to delete article: " + (data.error || "Unknown error")
              );
            }
          })
          .catch((error) => {
            console.error("Error deleting article:", error);
            alert("Error deleting article: " + error.message);
          });
      });
    });
  }

  // Delete all non-JUFO ranked button
  const deleteNotJufoBtn = document.getElementById("deleteNotJufoBtn");

  if (deleteNotJufoBtn) {
    deleteNotJufoBtn.addEventListener("click", function () {
      if (
        !confirm(
          "Are you sure you want to delete all non-JUFO ranked articles? This cannot be undone."
        )
      ) {
        return;
      }

      const keywords = document
        .querySelector(".centered-title")
        ?.getAttribute("data-keywords");

      if (!keywords) {
        alert("Cannot determine keywords for this search.");
        return;
      }

      fetch("/api/history/non_jufo", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          keywords: keywords,
        }),
      })
        .then((response) => {
          if (!response.ok)
            throw new Error("Failed to delete non-JUFO articles");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            // Reload the page to reflect changes
            window.location.reload();
          } else {
            alert(
              "Failed to delete non-JUFO articles: " +
                (data.error || "Unknown error")
            );
          }
        })
        .catch((error) => {
          console.error("Error deleting non-JUFO articles:", error);
          alert("Error deleting non-JUFO articles: " + error.message);
        });
    });
  }

  // History delete buttons
  const historyDeleteBtns = document.querySelectorAll(".delete-btn");

  if (historyDeleteBtns.length > 0) {
    historyDeleteBtns.forEach((btn) => {
      btn.addEventListener("click", function () {
        if (
          !confirm(
            "Are you sure you want to delete this search? This cannot be undone."
          )
        ) {
          return;
        }

        const keywords = this.getAttribute("data-keywords");

        fetch("/api/history", {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            keywords: keywords,
          }),
        })
          .then((response) => {
            if (!response.ok) throw new Error("Failed to delete search");
            return response.json();
          })
          .then((data) => {
            if (data.status === "success") {
              // Remove row from table
              const row = this.closest("tr");
              if (row) {
                row.remove();
              }
            } else {
              alert(
                "Failed to delete search: " + (data.error || "Unknown error")
              );
            }
          })
          .catch((error) => {
            console.error("Error deleting search:", error);
            alert("Error deleting search: " + error.message);
          });
      });
    });
  }
});
