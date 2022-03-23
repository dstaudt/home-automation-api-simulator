function update_state(control_state) {

    document.getElementById('blind').checked = control_state.blinds_down;
    document.getElementById('light').checked = control_state.lights_on;
    if (control_state.coffee_on) {
        if (TEST) {
            document.getElementById('pour').classList.add('drinksstatic');
            return;
        }
        document.getElementById('pour').classList.add('drinks');
        ['1', '2', '3', '4'].forEach((index) => {
            document.getElementById(`bubble${index}`).classList.add(`steam${index}`)
        })
    }
    else {
        if (TEST) {
            try { document.getElementById('pour').classList.remove('drinksstatic') } catch { };
            return;
        }
        if (document.querySelector('.drinks'))
            document.querySelector('.drinks').onanimationiteration = () => {
                document.getElementById('pour').classList.remove('drinks')
            }, { once: true };
        document.querySelector('.steam').onanimationiteration = () => {
            ['1', '2', '3', '4'].forEach((index) => {
                document.getElementById(`bubble${index}`).classList.remove(`steam${index}`)
            })
        }, { once: true };
    }
}

var source;
var control_state = {
    "blinds_down": false,
    "lights_on": false,
    "coffee_on": false
}

document.addEventListener('DOMContentLoaded', () => {
    update_state(control_state);
    connect_source();
    document.querySelector('.copybutton').addEventListener('click', event => {
        navigator.clipboard.writeText(document.getElementById('copystring').textContent);
        document.getElementById('status').textContent = 'Copied!';
        document.getElementById('status').classList.add('copy');
        window.setTimeout(() => { document.querySelector('.status').classList.remove('copy') }, 2000)
    });
});

function connect_source() {
    source = new EventSource(`/events/${deviceId}`);
    source.onmessage = (msg) => {
        if (msg.data == 'keepalive') return;
        if (msg.data == 'reconnected') {
            document.getElementById('status').classList.remove('reconnecting');
            return;
        }
        control_state = { ...control_state, ...JSON.parse(msg.data) };
        update_state(control_state);
    }
    source.onerror = (event) => {
        document.getElementById('status').textContent = 'Reconnecting...';
        document.getElementById('status').classList.add('reconnecting');
        setTimeout(() => {
            if (source.readyState == 2) connect_source()
        }, 5000);
    }
}

window.addEventListener('onunload', () => {
    if (source) { source.close() }
})


