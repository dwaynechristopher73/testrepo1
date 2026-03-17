// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function () {
  setTimeout(function () {
    document.querySelectorAll('.alert.alert-success, .alert.alert-info').forEach(function (el) {
      var alert = bootstrap.Alert.getOrCreateInstance(el);
      if (alert) alert.close();
    });
  }, 5000);
});
