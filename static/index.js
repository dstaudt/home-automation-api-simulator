function update(control_state) {
   document.querySelector('.copybutton').addEventListener('click', event => {
      navigator.clipboard.writeText(document.getElementById('copystring').textContent);
      document.querySelector('.copied').classList.add('copy');
      window.setTimeout(() => { document.querySelector('.copied').classList.remove('copy') }, 2000)
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

var source = new EventSource(`/events/${deviceId}`);
source.onmessage = function (msg) { update(control_state = JSON.parse(msg.data)) }

document.addEventListener('DOMContentLoaded', () => { update(control_state) });