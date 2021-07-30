var mon = [1, 2, 3, 4, 15, 46, 67, 78, 89, 80, 81, 82, 83, 84, 5, 6, 7, 8, 9, 0, 1, 2, 3, 4];
var tue = [11, 21, 13, 14, 15, 6, 7, 78, 9, 0, 81, 82, 3, 84, 15, 16, 7, 18, 19, 0, 1, 2, 13, 4];
var days = {};
days["day1"] = mon;
days["day2"] = tue;

var weeks = {};
week1 = ["day1", "day1", "day1", "day1", "day1", "day2", "day2"];
week2 = ["day1", "day2", "day2", "day2", "day1", "day1", "day2"];
week3 = ["day2", "day2", "day1", "day1", "day2", "day2", "day2"];
weeks["Parking Lot"] = week1;
weeks["Main Street"] = week2;
weeks["Indoor"] = week3;

function appendSliders() {
    for (i = 0; i < 24; i++) {
        var outerDiv = $('<div style="float: left;"></div>');
        var innerDiv = $('<div class="slider vertical" data-slider data-initial-start="25" data-end="100" data-vertical="true" id="slider' + i + '" >')
        var sliderSpan = $('<span class="slider-handle" data-slider-handle role="slider" tabindex="1" aria-controls="sliderOutput' + i + '"></span>')
        var sliderSpan2 = $('<span class="slider-fill" data-slider-fill></span>')
        var innerDiv2 = $('<div style="width :1cm;"></div>')
            .append('<input type="tel" style="padding-right: 0.3rem;padding-left: 0.3rem;" id="sliderOutput' + i + '">')
            .append('<small>' + i + ':00</small>')
        var label = $('<small>3:00</small>')
        innerDiv.append(sliderSpan, sliderSpan2)
        outerDiv.append(innerDiv, innerDiv2)
        $("#sliders").append(outerDiv);
    }
    $(".slider").foundation();
}

function assignSliderValue(values) {
    for (i = 0; i < 24; i++) {
        mySlider = new Foundation.Slider($("#slider" + i), {
            initialStart: values[i]
        });
    }
}

function assignDaysValue(values) {
    for (i = 0; i < 7; i++) {
        console.log("set the value")
        mySlider = new Foundation.Slider($("#slider" + i), {
            initialStart: values[i]
        });
    }
}

function reinitSlider() {
    var e = document.getElementById("daysProfile");
    var dayValue = e.options[e.selectedIndex].value;
    $("#dayProfileName").val(dayValue);
    console.log(dayValue)
    assignSliderValue(days[dayValue])
}

function reinitWeekDays() {
    var e = document.getElementById("weekProfile");
    var weekValue = e.options[e.selectedIndex].value;
    $("#weekProfileName").val(weekValue);
    for (i = 0; i < 7; i++) {
        $("#weekday" + i).val(weeks[weekValue][i]);
    }

}

function reinitDaysOption() {
    $("#daysProfile").empty();
    Object.keys(days).forEach(element => {
        var outerDiv = $('<div style="float: left;"></div>');
        $("#daysProfile").append('<option value="' + element + '">' + element + '</option>');
    });

}

function reinitWeekOption() {
    $("#weekProfile").empty();
    Object.keys(weeks).forEach(element => {
        var outerDiv = $('<div style="float: left;"></div>');
        $("#weekProfile").append('<option value="' + element + '">' + element + '</option>');
    });

}

function reinitWeekDayOption() {
    for (i = 0; i < 7; i++) {
        $("#weekday" + i).empty();
        Object.keys(days).forEach(element => {
            var outerDiv = $('<div style="float: left;"></div>');
            $("#weekday" + i).append('<option value="' + element + '">' + element + '</option>');
        });
    }

}

function reinitDays() {
    var e = document.getElementById("weekProfile");
    var weekVal = e.options[e.selectedIndex].value;
    reinitWeekDays();
    console.log(weekVal)
}

function getDimValues() {
    var dimValues = []
    for (i = 0; i < 24; i++) {
        dimValues.push($("#sliderOutput" + i).val())
    }
    console.log(dimValues)
    return dimValues
}


function getWeekValues() {
    var weekValues = []
    for (i = 0; i < 7; i++) {
        var e = document.getElementById("weekday" + i);
        var weekVal = e.options[e.selectedIndex].value;
        weekValues.push(weekVal)
    }
    console.log(weekValues)
    return weekValues
}

function saveDimValues() {
    dimValues = getDimValues();
    dayName = $("#dayProfileName").val();
    days[dayName] = dimValues;
    reinitDaysOption();
    $('#daysProfile').val(dayName);
    postDBDimValues();
}


function saveWeekValues() {
    weekValues = getWeekValues();
    weekName = $("#weekProfileName").val();
    weeks[weekName] = weekValues;
    reinitWeekOption();
    $('#weekProfile').val(weekName);
    postDBWeekValues();
}

function getDBDimValues() {
    var local_days
    $.ajax({
        method: 'GET',
        url: _endpoints.schedularDay,
        contentType: 'application/json',
        success: function () {
            console.log("Get day scheduler done")
        },
        error: function ajaxError(jqXHR, textStatus, errorThrown) {
            console.error('Error toggling address: ', textStatus, ', Details: ', errorThrown);
            console.error('Response: ', jqXHR.responseText);
        }
    }).done(async (data) => {
        local_days = await arrToDict(data["Items"]);
        days = local_days
        await reinitDaysOption();
        var e = await document.getElementById("daysProfile");
        var dayValue = await e.options[e.selectedIndex].value;
        $("#dayProfileName").val(dayValue);
        appendSliders()
        assignSliderValue(days["day1"]);
        reinitWeekDayOption();
        //reinitWeekDays();
    });
    return local_days;
}

function getDBWeekValues() {
    var local_days
    $.ajax({
        method: 'GET',
        url: _endpoints.schedularWeek,
        contentType: 'application/json',
        success: function () {
            console.log("Get week scheduler done")
        },
        error: function ajaxError(jqXHR, textStatus, errorThrown) {
            console.error('Error toggling address: ', textStatus, ', Details: ', errorThrown);
            console.error('Response: ', jqXHR.responseText);
        }
    }).done(function (data) {
        local_week = arrToDict(data["Items"]);
        weeks = local_week
        reinitWeekOption();
        var e = document.getElementById("weekProfile");
        var weekValue = e.options[e.selectedIndex].value;
        $("#weekProfileName").val(weekValue);
        // appendSliders()
        // assignSliderValue(days["day1"]);
        // console.log(local_days)
        // reinitWeekDayOption();
        // reinitWeekDays();
    });
    return local_days;
}

function postDBDimValues() {
    var e = document.getElementById("daysProfile");
    var dayValue = e.options[e.selectedIndex].value;
    $("#dayProfileName").val(dayValue);
    $.ajax({
        method: 'POST',
        url: _endpoints.schedularDay,
        data: JSON.stringify({
            id: dayValue,
            hour: days[dayValue]
        }),
        contentType: 'application/json',
        success: function () {
            console.log("saved successfully !!")
        },
        error: function ajaxError(jqXHR, textStatus, errorThrown) {
            console.error('Error toggling address: ', textStatus, ', Details: ', errorThrown);
            console.error('Response: ', jqXHR.responseText);
        }
    }).done(function (data) {});
}


function postDBWeekValues() {
    var e = document.getElementById("weekProfile");
    var weekValue = e.options[e.selectedIndex].value;
    $("#weekProfileName").val(weekValue);
    $.ajax({
        method: 'POST',
        url: _endpoints.schedularWeek,
        data: JSON.stringify({
            id: weekValue,
            hour: weeks[weekValue]
        }),
        contentType: 'application/json',
        success: function () {
            console.log("saved successfully !!")
        },
        error: function ajaxError(jqXHR, textStatus, errorThrown) {
            console.error('Error toggling address: ', textStatus, ', Details: ', errorThrown);
            console.error('Response: ', jqXHR.responseText);
        }
    }).done(function (data) {});

}

function arrToDict(arr) {
    dict = {}
    arr.forEach(element => {
        key = element["id"]
        dict[key] = element["hour"]
    });
    return dict
}

async function prepSchedularCanvas(){
    await $('#ice-content').replaceWith(schedularUI.canvas());
    // await $(document).foundation();
    await getDBDimValues();
    await getDBWeekValues();
    await $('#ice-content').foundation();
}