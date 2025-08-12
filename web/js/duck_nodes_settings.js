import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

app.registerExtension({
	name: "Duck Nodes.Settings", 
	async setup() {
		let currentSettings = {
			enabled: true,
			language: "en"
		};
		try {
			const resp = await api.fetchApi("/duck_nodes/settings");
			if (resp.ok) {
				currentSettings = await resp.json();
			} else {
				console.error("Could not fetch Duck Nodes settings.");
			}
		} catch (e) {
			console.error("Error fetching Duck Nodes settings:", e);
		}

		const saveSettings = (key, value) => {
			const newSettings = { ...currentSettings, [key]: value };
			
			api.fetchApi("/duck_nodes/settings", {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(newSettings),
			})
			.then(resp => {
				if (!resp.ok) {
					console.error("Failed to update Duck Nodes setting. Status:", resp.status);
					return Promise.reject("Server error");
				}
				return resp.json();
			})
			.then(result => {
				if (!result) return;
				console.log(`Duck Nodes: Settings updated`, newSettings);
				currentSettings = newSettings; 
				if(result.status === 'requires_setup') {
					console.log("Login enabled, but no password is set. Please go to the login page to complete the setup.");
				}
			})
			.catch(e => {
				if (e !== "Server error") {
					console.error("Error saving Duck Nodes setting:", e);
				}
			});
		};


		app.ui.settings.addSetting({
			id: "Duck Nodes.EnableLogin",
			name: "Duck Nodes: Enable Login",
			type: "boolean",
			defaultValue: currentSettings.enabled,
			onChange: (value) => {
				saveSettings("enabled", value);
			},
		});
	},
});
