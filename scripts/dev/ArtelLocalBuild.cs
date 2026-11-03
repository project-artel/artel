using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

public static class ArtelLocalBuild
{
    public static void BuildWindows64()
    {
        var args = Environment.GetCommandLineArgs();
        var index = Array.IndexOf(args, "-artelBuildPath");
        if (index < 0 || index + 1 >= args.Length)
            throw new ArgumentException("-artelBuildPath가 필요합니다.");
        var output = args[index + 1];
        var scenes = EditorBuildSettings.scenes.Where(scene => scene.enabled).Select(scene => scene.path).ToArray();
        if (scenes.Length == 0)
            throw new InvalidOperationException("Build Settings에 활성화된 scene이 없습니다.");
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = output,
            target = BuildTarget.StandaloneWindows64,
            targetGroup = BuildTargetGroup.Standalone,
            options = BuildOptions.Development,
            extraScriptingDefines = new[] { "ARTEL_GAME_FUNCTIONS" },
        });
        if (report.summary.result != BuildResult.Succeeded)
            throw new InvalidOperationException($"빌드 실패: {report.summary.result}, errors={report.summary.totalErrors}");
        File.WriteAllText(output + ".success", PlayerSettings.bundleVersion);
        Debug.Log($"[ArtelLocalBuild] success version={PlayerSettings.bundleVersion} scenes={scenes.Length}");
        EditorApplication.Exit(0);
    }
}
