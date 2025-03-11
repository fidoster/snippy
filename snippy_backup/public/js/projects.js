document.addEventListener("DOMContentLoaded", function () {
  console.log("Projects JS loaded.");

  // Make card headers clickable to toggle collapse
  const cardHeaders = document.querySelectorAll(".card-header");
  cardHeaders.forEach(function (header) {
    header.addEventListener("click", function (e) {
      // Do not toggle if the click is on a button or within a form
      if (
        e.target.tagName.toLowerCase() === "button" ||
        e.target.closest("form")
      ) {
        return;
      }
      const collapseDiv = header.nextElementSibling;
      if (collapseDiv && collapseDiv.classList.contains("collapse")) {
        let collapseInstance = bootstrap.Collapse.getInstance(collapseDiv);
        if (!collapseInstance) {
          collapseInstance = new bootstrap.Collapse(collapseDiv, {
            toggle: false,
          });
        }
        collapseInstance.toggle();
      }
    });
  });

  // Handle project creation
  const projectForm = document.getElementById("projectForm");
  if (projectForm) {
    projectForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const title = document.getElementById("title").value;
      const description = document.getElementById("description").value;

      fetch("/api/projects", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title,
          description: description,
        }),
      })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            window.location.href = "/projects";
          } else {
            alert(
              "Failed to create project: " + (data.error || "Unknown error")
            );
          }
        })
        .catch((error) => {
          console.error("Error creating project:", error);
          alert("Error creating project: " + error.message);
        });
    });
  }

  // Handle project deletion
  const deleteProjectBtns = document.querySelectorAll(".delete-project-btn");
  deleteProjectBtns.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      if (!confirm("Are you sure you want to delete this project?")) {
        return;
      }

      const projectId = this.getAttribute("data-project-id");

      fetch(`/api/projects/${projectId}`, {
        method: "DELETE",
      })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            // Remove the project card or refresh the page
            const projectCard = this.closest(".project-card");
            if (projectCard) {
              projectCard.remove();
            } else {
              window.location.reload();
            }
          } else {
            alert(
              "Failed to delete project: " + (data.error || "Unknown error")
            );
          }
        })
        .catch((error) => {
          console.error("Error deleting project:", error);
          alert("Error deleting project: " + error.message);
        });
    });
  });

  // Handle section creation
  const sectionForms = document.querySelectorAll(".add-section-form");
  sectionForms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const projectId = this.getAttribute("data-project-id");
      const titleInput = this.querySelector('input[name="title"]');
      const title = titleInput.value;

      fetch(`/api/projects/${projectId}/sections`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title,
        }),
      })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            window.location.reload();
          } else {
            alert("Failed to add section: " + (data.error || "Unknown error"));
          }
        })
        .catch((error) => {
          console.error("Error adding section:", error);
          alert("Error adding section: " + error.message);
        });
    });
  });

  // Handle section deletion
  const deleteSectionBtns = document.querySelectorAll(".delete-section-btn");
  deleteSectionBtns.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      if (!confirm("Are you sure you want to delete this section?")) {
        return;
      }

      const projectId = this.getAttribute("data-project-id");
      const sectionId = this.getAttribute("data-section-id");

      fetch(`/api/projects/${projectId}/sections/${sectionId}`, {
        method: "DELETE",
      })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            // Remove the section card or refresh the page
            const sectionCard = this.closest(".section-card");
            if (sectionCard) {
              sectionCard.remove();
            } else {
              window.location.reload();
            }
          } else {
            alert(
              "Failed to delete section: " + (data.error || "Unknown error")
            );
          }
        })
        .catch((error) => {
          console.error("Error deleting section:", error);
          alert("Error deleting section: " + error.message);
        });
    });
  });

  // Handle search block addition
  const searchBlockForms = document.querySelectorAll(".search-block-form");
  searchBlockForms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();

      const projectId = this.getAttribute("data-project-id");
      const sectionId = this.getAttribute("data-section-id");
      const keywordsSelect = this.querySelector('select[name="keywords"]');
      const keywords = keywordsSelect.value;

      if (!keywords) {
        alert("Please select search keywords");
        return;
      }

      fetch(`/api/projects/${projectId}/sections/${sectionId}/search_block`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          keywords: keywords,
        }),
      })
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            window.location.reload();
          } else {
            alert(
              "Failed to add search block: " + (data.error || "Unknown error")
            );
          }
        })
        .catch((error) => {
          console.error("Error adding search block:", error);
          alert("Error adding search block: " + error.message);
        });
    });
  });

  // Handle article deletion
  const deleteArticleBtns = document.querySelectorAll(".delete-article-btn");
  deleteArticleBtns.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      if (!confirm("Are you sure you want to delete this article?")) {
        return;
      }

      const projectId = this.getAttribute("data-project-id");
      const sectionId = this.getAttribute("data-section-id");
      const articleId = this.getAttribute("data-article-id");

      fetch(
        `/api/projects/${projectId}/sections/${sectionId}/articles/${articleId}`,
        {
          method: "DELETE",
        }
      )
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            // If it's a search block, remove the whole block
            const searchBlock = this.closest(".keyword-card");
            if (searchBlock) {
              searchBlock.remove();
            } else {
              // Otherwise, remove just the row
              const row = this.closest("tr");
              if (row) {
                row.remove();
              } else {
                window.location.reload();
              }
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

  // Handle article deletion from search block
  const deleteFromBlockBtns = document.querySelectorAll(
    ".delete-from-block-btn"
  );
  deleteFromBlockBtns.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      if (
        !confirm("Are you sure you want to delete this article from the block?")
      ) {
        return;
      }

      const projectId = this.getAttribute("data-project-id");
      const sectionId = this.getAttribute("data-section-id");
      const blockId = this.getAttribute("data-block-id");
      const articleIndex = this.getAttribute("data-article-index");

      fetch(
        `/api/projects/${projectId}/sections/${sectionId}/search_block/${blockId}/article/${articleIndex}`,
        {
          method: "DELETE",
        }
      )
        .then((response) => {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.json();
        })
        .then((data) => {
          if (data.status === "success") {
            // Remove just the row
            const row = this.closest("tr");
            if (row) {
              row.remove();
            } else {
              window.location.reload();
            }
          } else {
            alert(
              "Failed to delete article from block: " +
                (data.error || "Unknown error")
            );
          }
        })
        .catch((error) => {
          console.error("Error deleting article from block:", error);
          alert("Error deleting article from block: " + error.message);
        });
    });
  });
});
