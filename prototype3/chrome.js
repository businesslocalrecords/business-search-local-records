(function () {
  var signin = document.getElementById("signin");
  var sub = document.getElementById("headsub");
  var account = document.getElementById("nav-account");
  var city = new URLSearchParams(location.search).get("city");
  if (city) {
    var home = "./?city=" + encodeURIComponent(city);
    document.querySelectorAll("a").forEach(function (a) {
      var href = a.getAttribute("href");
      if (href === "./") a.href = home;
      if (href === "./#signin") a.href = home + "#signin";
    });
  }
  document.querySelectorAll(".sections a").forEach(function (a) {
    var path = a.getAttribute("data-path");
    if (!path) return;
    a.href = city ? path + "?city=" + encodeURIComponent(city) : path;
  });
  var bar = document.querySelector(".top");
  if (bar) document.body.style.paddingTop = bar.offsetHeight + "px";
  if (sub) {
    var query = [];
    if (city) query.push("city=" + encodeURIComponent(city));
    var here = location.pathname + location.search;
    if (here.charAt(0) === "/" && here.indexOf("checkout.html") === -1 && here.indexOf("signup.html") === -1 && here.indexOf("thanks.html") === -1) {
      query.push("next=" + encodeURIComponent(here));
    }
    if (query.length) sub.href = "checkout.html?" + query.join("&");
  }
  if (account) account.href = city ? "portal.html?city=" + encodeURIComponent(city) : "portal.html";
  fetch("/api/index.php?r=me", {credentials: "same-origin"}).then(function (res) {
    return res.json();
  }).then(function (data) {
    if (!data || !data.email) return;
    if (account) account.hidden = false;
    if (data.subscribed && sub) sub.hidden = true;
    if (signin) {
      signin.textContent = "Sign out";
      signin.href = "#";
      signin.addEventListener("click", function (e) {
        e.preventDefault();
        fetch("/api/index.php?r=logout", {method: "POST", credentials: "same-origin"}).finally(function () {
          location.reload();
        });
      });
    }
    document.dispatchEvent(new CustomEvent("rpr-session", {detail: data}));
  }).catch(function () {});
})();
