const fs=require("fs"); const path=require("path");
const src=path.join(__dirname,"vercel_portal"); const out=path.join(__dirname,"vercel_dist");
fs.rmSync(out,{recursive:true,force:true}); fs.mkdirSync(out,{recursive:true}); fs.cpSync(src,out,{recursive:true});
if(!fs.existsSync(path.join(out,"index.html"))) throw new Error("vercel_portal/index.html ausente");
console.log("Static launcher built. Python local runtime is intentionally not deployed.");
