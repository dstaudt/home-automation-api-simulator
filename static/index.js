function update_state(control_state) {
    document.querySelector('.copybutton').addEventListener('click', event => {
        navigator.clipboard.writeText(document.getElementById('copystring').textContent);
        document.getElementById('status').textContent = 'Copied!';
        document.getElementById('status').classList.add('copy');
        window.setTimeout(() => { document.querySelector('.status').classList.remove('copy') }, 2000)
    });
    document.getElementById('blind').checked = control_state.blinds_down;
    document.getElementById('light').checked = control_state.lights_on;
    if (control_state.coffee_on == true) {
        document.getElementById('bubble1').classList.add('steam1');
        document.getElementById('bubble2').classList.add('steam2');
        document.getElementById('bubble3').classList.add('steam3');
        document.getElementById('bubble4').classList.add('steam4');
        document.getElementById('pour').classList.add('drinks')
    }
    else {
        document.querySelector('.steam').addEventListener('animationiteration', () => {
            document.getElementById('bubble1').classList.remove('steam1');
            document.getElementById('bubble2').classList.remove('steam2');
            document.getElementById('bubble3').classList.remove('steam3');
            document.getElementById('bubble4').classList.remove('steam4');
        }, { once: true });
        if (document.querySelector('.drinks'))
            document.querySelector('.drinks').addEventListener('animationiteration', () => {
                document.getElementById('pour').classList.remove('drinks')
            }, { once: true });
    }
}

var source;

document.addEventListener('DOMContentLoaded', () => {
    update_state(control_state)
    connect_source()
});

function connect_source() {
    source = new EventSource(`/events/${deviceId}`);

    source.onmessage = function (msg) { 
        if (msg.data == 'reconnected') {
            document.getElementById('status').classList.remove('reconnecting');
            return;
        }
        update_state(control_state = JSON.parse(msg.data))
    }
    source.onerror = function (event) {
        document.getElementById('status').textContent = 'Reconnecting...';
        document.getElementById('status').classList.add('reconnecting');
        setTimeout(() => {
            if (source.readyState == 2) { connect_source() }
        }, 5000);
    }
}

window.onunload = function() { 
    if (source) { source.close()}
}


