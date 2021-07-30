let loadLcmApp = {
    start: async function(){
        await loadLcmApp.prepCanvas();
    },

    prepCanvas: async function(){
        await $('#ice-content').replaceWith(loadlcmUI.canvas());
    },

    file: null,

    setFile: function(file){
        loadLcmApp.file = file;
    },

    getFile: function(){
        return loadLcmApp.file;
    },

    loadfile: function(file) {
        loadLcmApp.setFile(file[0]);
    },

    sendlcm: function(){
        var reader = new FileReader();
        let file = loadLcmApp.getFile();
        let lcms = []
        reader.onload = function(progressEvent){
            // Entire file
            // console.log(this.result);
        
            // By lines
            var lines = this.result.split('\n');
            for(var line = 0; line < lines.length; line++){
            //   console.log(lines[line]);
            lcms.push(loadLcmApp.prepareRequest(lines[line]));
            }
            if(lcms.length>0){
                loadLcmApp.sendlcmLoadRequest(lcms);
            }
          };
          reader.readAsText(file);
        
    },

    prepareRequest: function(line){
        // console.log(line);
        let splits = line.split(",",2);
        return {
            "ip": splits[0],
            "key": splits[1]
        }
    },

    sendlcmLoadRequest: function(lcms){
        loadCertifiedLcm({
            "lcms": lcms
        },function(){
            $('.loadlcm-success').show();
        }, function(err){
            $('.fi-alert').text(err);
            $('.loadlcm-fail').show();
        })
    }
}