#include <cstdio>
#include <cstdlib>
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <string>
#include <signal.h>
#include <vector>

#include <TRint.h>
#include <TStyle.h>
#include <TCanvas.h>
#include <TPad.h>
#include <TH2.h>
#include <TGraph.h>

#include "TCPclient.h"

using namespace std;

bool end_flag;

void end_seq(int)
{
	end_flag = 1;
}

int main(int argc, char *argv[])
{
	string IPaddr = "192.168.100.16";
	if (argc < 2)
	{
		cerr << " USAGE> DAQcheck [IP]" << endl;
	}
	else
	{
		IPaddr = argv[1];
	}

	TRint app("app", &argc, argv);
	gStyle->SetOptStat(0);

	cout << "IP: " << IPaddr << endl;
	//  TCPclient iwaki("192.168.100.16", 24);
	TCPclient iwaki(IPaddr.c_str(), 24);
	end_flag = 0;

	cout << hex;
	signal(SIGINT, end_seq);

	TCanvas *ViewWin = new TCanvas("ViewWin", "", 400, 0, 800, 600);
	TPad *pad0 = new TPad("pad0", "pad0", .0, .00, .8, 1.0);
	TPad *pad1 = new TPad("pad1", "pad1", .8, .75, 1., 1.0);
	TPad *pad2 = new TPad("pad2", "pad2", .8, .50, 1., .75);
	TPad *pad3 = new TPad("pad3", "pad3", .8, .25, 1., .50);
	TPad *pad4 = new TPad("pad4", "pad4", .8, .00, 1., .25);
	ViewWin->cd();
	pad0->Draw();
	pad1->Draw();
	pad2->Draw();
	pad3->Draw();
	pad4->Draw();

	//  TH2D *image = new TH2D("image", "", 128, -0.5, 127.5, 128, 999.5, 1127.5);
	TH2D *image = new TH2D("image", "", 128, -0.5, 127.5, 1024, -0.5, 1023.5);
	TH2D *frame = new TH2D("frame", "", 2, -0.5, 1023.5, 2, -0.5, 1023.5);
	pad1->cd();
	frame->Draw();
	pad2->cd();
	frame->Draw();
	pad3->cd();
	frame->Draw();
	pad4->cd();
	frame->Draw();

	TGraph **wave = new TGraph *[4];
	for (int i = 0; i < 4; i++)
		wave[i] = new TGraph;

	short event_data = 0;
	short footer = 0;
	vector<char> evt_data;
	//  char evt_data[30000];
	int checksize = 1000;
	cout << "idling..." << endl;
	while (iwaki.isAlive() && !end_flag)
	{
		char msg[checksize];
		int num = iwaki.RecieveMsg(msg, checksize);

		if (num > 0 && num < 28679)
		{
			for (int i = 0; i < num; i++)
			{
				//	if(i>28679)break;
				if ((event_data == 0 && (msg[i] & 0xff) == 0xeb) ||
					(event_data == 1 && (msg[i] & 0xff) == 0x90) ||
					(event_data == 2 && (msg[i] & 0xff) == 0x19) ||
					(event_data == 3 && (msg[i] & 0xff) == 0x64))
				{
					event_data++;
					evt_data.push_back(msg[i]);
					image->Reset();
				}
				else if (event_data == 4 || event_data == 5 ||
						 event_data == 6 || event_data == 7 ||
						 event_data == 8 || event_data == 9 ||
						 event_data == 10 || event_data == 11 ||
						 event_data == 12 || event_data == 13 ||
						 event_data == 14 || event_data == 15)
				{
					event_data++;
					evt_data.push_back(msg[i]);
				}
				else if (event_data == 16)
				{
					if ((msg[i] & 0xff) == 0x75)
						footer = footer | 0x1;
					else if ((msg[i] & 0xff) == 0x50 && footer == 0x1)
						footer = footer | 0x2;
					else if ((msg[i] & 0xff) == 0x49 && footer == 0x3)
						footer = footer | 0x4;
					else if ((msg[i] & 0xff) == 0x43 && footer == 0x7)
						footer = footer | 0x8;
					else
						footer = 0;

					evt_data.push_back(msg[i]);

					if (footer == 0xf)
						event_data++;
				}
				else
				{
					event_data = 0;
					evt_data.clear();
				}

				if (event_data > 16)
				{
					unsigned evt_cnt = ((evt_data.at(4) & 0xff) << 24) | ((evt_data.at(5) & 0xff) << 16) | ((evt_data.at(6) & 0xff) << 8) | (evt_data.at(7) & 0xff);
					unsigned clk_cnt = ((evt_data.at(8) & 0xff) << 24) | ((evt_data.at(9) & 0xff) << 16) | ((evt_data.at(10) & 0xff) << 8) | (evt_data.at(11) & 0xff);
					unsigned trg_cnt = ((evt_data.at(12) & 0xff) << 24) | ((evt_data.at(13) & 0xff) << 16) | ((evt_data.at(14) & 0xff) << 8) | (evt_data.at(15) & 0xff);

					for (int i = 0; i < 4; i++)
						cout << hex << setw(2) << setfill('0') << (evt_data.at(i) & 0xff) << " ";
					cout << dec;
					cout << endl
						 << "trig counter" << setw(8) << setfill('0') << evt_cnt << " "
						 << endl
						 << "clock counter" << setw(8) << setfill('0') << clk_cnt << " "
						 << endl
						 << "signal counter" << setw(8) << setfill('0') << trg_cnt << endl;
					cout << evt_data.size() << endl;

					if (evt_data.size() > 20)
					{
						for (int i = 0; i < 1024; i++)
						{
							for (int ch = 0; ch < 4; ch++)
							{
								unsigned fadc = ((evt_data.at(i * 8 + ch * 2 + 16) & 0xff) << 8) | (evt_data.at(i * 8 + ch * 2 + 17) & 0xff);

								wave[ch]->SetPoint(i, i, fadc & 0x3ff);
							}
						}

						cout << setw(2) << setfill('0') << (evt_data.at(8208) & 0xff)
							 << setw(2) << setfill('0') << (evt_data.at(8209) & 0xff)
							 << setw(2) << setfill('0') << (evt_data.at(8210) & 0xff)
							 << setw(2) << setfill('0') << (evt_data.at(8211) & 0xff)
							 << endl;

						int offset = 8212;
						unsigned flag = ((evt_data.at(offset + 0) & 0xff) << 24) | ((evt_data.at(offset + 1) & 0xff) << 16) | ((evt_data.at(offset + 2) & 0xff) << 8) | (evt_data.at(offset + 3) & 0xff);
						while (flag != 0x75504943)
						{
							int clk = ((evt_data.at(offset + 2) & 0x07) << 8) | (evt_data.at(offset + 3) & 0xff);
							for (int i = 0; i < 16; i++)
							{
								for (int j = 0; j < 8; j++)
								{
									if ((evt_data.at(offset + i + 4) >> (7 - j)) & 0x1)
									{
										image->Fill((7 - j) + 8 * (15 - i), clk);
										//		    cout << "(i, j, clk)= "<<i<<" "<<j<<" "<<clk<<endl;
									}
								}
							}

							offset += 20;
							flag = ((evt_data.at(offset + 0) & 0xff) << 24) | ((evt_data.at(offset + 1) & 0xff) << 16) | ((evt_data.at(offset + 2) & 0xff) << 8) | (evt_data.at(offset + 3) & 0xff);
						}
						cout << flag << endl;
					}
					else
					{
						for (int i = 0; i < 1024; i++)
							for (int ch = 0; ch < 4; ch++)
								wave[ch]->SetPoint(i, i, -1000);
					}

					cout << endl;
					event_data = 0;
					evt_data.clear();
					pad0->cd();
					image->Draw("col");
					pad1->cd();
					wave[0]->Draw("p");
					pad2->cd();
					wave[1]->Draw("p");
					pad3->cd();
					wave[2]->Draw("p");
					pad4->cd();
					wave[3]->Draw("p");

					ViewWin->cd();
					ViewWin->Update();
					//	  sleep(5);
				}
			}
		}
	}

	cout << dec;
	signal(SIGINT, SIG_DFL);
	iwaki.Close();
}
