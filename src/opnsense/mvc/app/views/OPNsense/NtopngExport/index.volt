<script>
    $(document).ready(function () {
        // default to today (local time of the browser)
        var d = new Date();
        var pad = function (n) { return (n < 10 ? '0' : '') + n; };
        var today = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
        $("#day").val(today).attr('max', today);

        $("#exportAct").click(function () {
            var day = $("#day").val();
            var ip = $("#ip").val();
            $("#exportMsg").addClass("hidden");
            if (!day || !ip) {
                $("#exportMsg").removeClass("hidden").text("{{ lang._('Please select a day and an IP address.') }}");
                return;
            }
            $("#exportAct_progress").addClass("fa fa-spinner fa-pulse");
            ajaxCall("/api/ntopngexport/export/csv", {day: day, ip: ip}, function (data, status) {
                $("#exportAct_progress").removeClass("fa fa-spinner fa-pulse");
                if (data && data.status === 'ok') {
                    var blob = new Blob([data.csv], {type: 'text/csv;charset=utf-8'});
                    var a = document.createElement('a');
                    a.href = URL.createObjectURL(blob);
                    a.download = data.filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
                } else {
                    var msg = (data && data.message) ? data.message : "{{ lang._('Export failed.') }}";
                    $("#exportMsg").removeClass("hidden").text(msg);
                }
            });
        });
    });
</script>

<div class="content-box" style="padding: 1.5em;">
    <div class="alert alert-danger hidden" role="alert" id="exportMsg"></div>
    {% if hosts|length == 0 %}
    <div class="alert alert-warning" role="alert">
        {{ lang._('No hosts configured. Add at least one IP address in the Settings page.') }}
    </div>
    {% else %}
    <div class="form-group" style="max-width: 320px;">
        <label for="day">{{ lang._('Day') }}</label>
        <input type="date" class="form-control" id="day"/>
    </div>
    <div class="form-group" style="max-width: 320px;">
        <label for="ip">{{ lang._('IP address') }}</label>
        <select class="form-control" id="ip">
            {% for host in hosts %}
            <option value="{{ host|e }}">{{ host|e }}</option>
            {% endfor %}
        </select>
    </div>
    <button class="btn btn-primary" id="exportAct" type="button">
        <b>{{ lang._('Download CSV') }}</b> <i id="exportAct_progress"></i>
    </button>
    {% endif %}
</div>
